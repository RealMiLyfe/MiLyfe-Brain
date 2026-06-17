"""MiLyfe Brain — BaseAgent ABC (optimized think/act loop with streaming, pooling, smart context)."""

from __future__ import annotations

import abc
import asyncio
import time
import uuid
from datetime import datetime
from typing import Any, AsyncGenerator, Dict, List, Optional

import httpx
import structlog

from config import settings
from models.schemas import (
    AgentRole,
    AgentState,
    EventType,
    StreamEvent,
    ToolCall,
    ToolResult,
)

logger = structlog.get_logger()

# ─── Shared Connection Pool (reuse across all agents) ─────────
_http_pool: Optional[httpx.AsyncClient] = None


async def get_http_pool() -> httpx.AsyncClient:
    """Get or create the shared connection pool."""
    global _http_pool
    if _http_pool is None or _http_pool.is_closed:
        _http_pool = httpx.AsyncClient(
            timeout=httpx.Timeout(settings.agent_timeout, connect=10.0),
            limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
        )
    return _http_pool


class BaseAgent(abc.ABC):
    """Abstract base class for all MiLyfe Brain agents.

    Optimized think/act loop with:
    - Connection pooling (shared httpx client)
    - Token-by-token streaming support
    - Smart context injection (rules, skills, env, scratchpad)
    - Context window management (auto-compaction)
    - Circuit breaker integration
    - Model fallback chain
    - Parallel tool execution
    - Learning from corrections
    """

    def __init__(
        self,
        role: AgentRole,
        agent_id: Optional[str] = None,
        model: Optional[str] = None,
        task: str = "",
        playbook_id: Optional[str] = None,
    ):
        self.id = agent_id or str(uuid.uuid4())
        self.role = role
        self.model = model or self._default_model()
        self.task = task
        self.name = self._role_name()
        self.avatar_color = self._avatar_color()
        self.playbook_id = playbook_id

        self._messages: List[Dict[str, str]] = []
        self._thoughts: List[str] = []
        self._actions_taken: int = 0
        self._progress: float = 0.0
        self._spawned_at = datetime.utcnow()
        self._total_tokens_used: int = 0
        self._total_duration_ms: float = 0.0
        self._corrections: List[str] = []  # User corrections for learning

    # ─── Abstract Methods ───────────────────────────────────────

    @abc.abstractmethod
    def system_prompt(self) -> str:
        """Return the system prompt for this agent role."""
        ...

    # ─── Public Interface ───────────────────────────────────────

    def get_state(self) -> AgentState:
        """Get current agent state for API/UI."""
        return AgentState(
            id=self.id,
            role=self.role,
            name=self.name,
            status="working" if self._messages else "idle",
            current_task=self.task,
            thoughts=self._thoughts[-5:],
            actions_taken=self._actions_taken,
            progress=self._progress,
            model=self.model,
            avatar_color=self.avatar_color,
            spawned_at=self._spawned_at,
        )

    async def think(
        self,
        task: str,
        context: Optional[Dict[str, Any]] = None,
        max_rounds: int = 3,
        stream: bool = False,
    ) -> str:
        """Execute the optimized think/act loop.

        Args:
            task: The task description
            context: Additional context dict
            max_rounds: Maximum tool-use rounds
            stream: If True, emit tokens as they arrive

        Returns:
            Final response text
        """
        self.task = task
        context = context or {}
        start_time = time.time()

        # 1. Recall relevant context (parallel: vector memory + long-term memory)
        relevant_context, learned_context = await asyncio.gather(
            self._recall_context(task),
            self._recall_learned_patterns(task),
            return_exceptions=True,
        )
        if isinstance(relevant_context, Exception):
            relevant_context = ""
        if isinstance(learned_context, Exception):
            learned_context = ""

        # 2. Build enriched system prompt
        system = self._build_enriched_system_prompt(
            relevant_context=relevant_context if isinstance(relevant_context, str) else "",
            learned_context=learned_context if isinstance(learned_context, str) else "",
            extra_context=context,
        )

        # 3. Initialize message history
        self._messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": task},
        ]

        self._emit_event(EventType.AGENT_SPAWNED, {
            "task": task[:200],
            "model": self.model,
            "context_tokens": len(system) // 4,
        })

        # 4. Tool loop with streaming support
        final_response = ""
        for round_num in range(max_rounds):
            # Check context window size, compact if needed
            await self._maybe_compact_context()

            # Call LLM (with circuit breaker + fallback)
            response_text = await self._call_llm_safe(stream=stream)

            if not response_text:
                final_response = "No response generated. Model may be unavailable."
                break

            # Record thought
            self._thoughts.append(response_text[:200])
            self._emit_event(EventType.THOUGHT, {
                "content": response_text[:500],
                "round": round_num,
                "tokens_so_far": self._total_tokens_used,
            })

            # Parse tool calls (supports multiple formats)
            from agents.tool_parser import parse_tool_calls
            tool_calls = parse_tool_calls(response_text)

            if not tool_calls:
                final_response = response_text
                break

            # Execute tools (parallel when possible)
            tool_results = await self._execute_tools_optimized(tool_calls)

            # Feed results back
            tool_output = self._format_tool_results(tool_results)
            self._messages.append({"role": "assistant", "content": response_text})
            self._messages.append({"role": "user", "content": f"Tool results:\n{tool_output}"})

            self._progress = (round_num + 1) / max_rounds

        # 5. Post-completion tasks (parallel, non-blocking)
        asyncio.create_task(self._post_completion(task, final_response, time.time() - start_time))

        self._progress = 1.0
        self._emit_event(EventType.COMPLETED, {
            "response_length": len(final_response),
            "rounds": len(self._thoughts),
            "duration_s": round(time.time() - start_time, 2),
            "total_tokens": self._total_tokens_used,
        })

        return final_response

    async def think_streaming(
        self,
        task: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> AsyncGenerator[str, None]:
        """Stream response tokens as they arrive from Ollama."""
        self.task = task
        context = context or {}

        # Build prompt (simplified for streaming - single turn)
        system = self._build_enriched_system_prompt(extra_context=context)
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": task},
        ]

        client = await get_http_pool()
        try:
            async with client.stream(
                "POST",
                f"{settings.ollama_base_url}/api/chat",
                json={
                    "model": self.model,
                    "messages": messages,
                    "stream": True,
                    "options": {"temperature": 0.7, "num_predict": 4096},
                },
            ) as response:
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    import orjson
                    try:
                        data = orjson.loads(line)
                        token = data.get("message", {}).get("content", "")
                        if token:
                            yield token
                            # Emit token event for WebSocket
                            self._emit_event(EventType.THOUGHT, {"token": token, "streaming": True})
                    except Exception:
                        continue
        except Exception as e:
            yield f"\n[Error: {e}]"

    def record_correction(self, correction: str):
        """Record a user correction for learning."""
        self._corrections.append(correction)

    # ─── LLM Interaction (Optimized) ────────────────────────────

    async def _call_llm_safe(self, stream: bool = False) -> str:
        """Call LLM with circuit breaker and model fallback."""
        try:
            from services.circuit_breaker import breakers
            breaker = breakers.get("ollama")

            if breaker:
                return await breaker.call(self._call_llm_pooled)
            return await self._call_llm_pooled()

        except Exception as e:
            # Try fallback chain
            logger.warning("llm_primary_failed", model=self.model, error=str(e))
            return await self._call_llm_fallback()

    async def _call_llm_pooled(self) -> str:
        """Call Ollama using shared connection pool."""
        client = await get_http_pool()

        resp = await client.post(
            f"{settings.ollama_base_url}/api/chat",
            json={
                "model": self.model,
                "messages": self._messages,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "num_predict": 4096,
                    "num_ctx": 8192,
                },
            },
        )

        if resp.status_code != 200:
            raise RuntimeError(f"Ollama HTTP {resp.status_code}: {resp.text[:200]}")

        data = resp.json()
        content = data.get("message", {}).get("content", "")

        # Track tokens
        prompt_tokens = data.get("prompt_eval_count", 0)
        completion_tokens = data.get("eval_count", 0)
        self._total_tokens_used += prompt_tokens + completion_tokens
        self._total_duration_ms += data.get("total_duration", 0) / 1_000_000

        # Async token tracking (don't wait)
        asyncio.create_task(self._track_tokens_async(data))

        return content

    async def _call_llm_fallback(self) -> str:
        """Try fallback models when primary fails."""
        try:
            from services.model_fallback import model_fallback
            result = await model_fallback.call_with_fallback(
                messages=self._messages,
                preferred_model=self.model,
            )
            return result.get("content", "")
        except Exception as e:
            logger.error("all_models_failed", error=str(e))
            return ""

    # ─── Tool Execution (Optimized) ────────────────────────────

    async def _execute_tools_optimized(self, tool_calls: List[ToolCall]) -> List[ToolResult]:
        """Execute tools with parallel execution for independent calls."""
        if len(tool_calls) == 1:
            return [await self._execute_single_tool(tool_calls[0])]

        # Check if tools can run in parallel (no file conflicts)
        if self._can_parallelize(tool_calls):
            tasks = [self._execute_single_tool(tc) for tc in tool_calls]
            return await asyncio.gather(*tasks)
        else:
            # Sequential execution for dependent tools
            results = []
            for tc in tool_calls:
                results.append(await self._execute_single_tool(tc))
            return results

    async def _execute_single_tool(self, tc: ToolCall) -> ToolResult:
        """Execute a single tool with hooks."""
        self._actions_taken += 1
        self._emit_event(EventType.TOOL_CALL, {"tool": tc.tool_name, "args": tc.arguments})

        try:
            from hooks.registry import hook_registry
            tc = await hook_registry.run_pre_hooks(tc, self)

            from tools.registry import tool_registry
            result = await tool_registry.execute(tc.tool_name, tc.arguments, agent=self)

            result = await hook_registry.run_post_hooks(result, self)

            self._emit_event(EventType.TOOL_RESULT, {
                "tool": tc.tool_name,
                "success": result.success,
                "output_preview": result.output[:200] if result.output else "",
                "execution_time_ms": result.execution_time_ms,
            })
            return result

        except Exception as e:
            return ToolResult(tool_name=tc.tool_name, success=False, error=str(e))

    def _can_parallelize(self, tool_calls: List[ToolCall]) -> bool:
        """Check if tool calls can safely run in parallel."""
        write_tools = {"file_write", "file_delete", "shell_exec"}
        paths_written = set()

        for tc in tool_calls:
            if tc.tool_name in write_tools:
                path = tc.arguments.get("path", tc.arguments.get("command", ""))
                if path in paths_written:
                    return False  # Conflict
                paths_written.add(path)

        return True

    # ─── Context Management ─────────────────────────────────────

    async def _maybe_compact_context(self):
        """Compact context if approaching token limits."""
        try:
            from services.context_manager import context_manager
            if context_manager.needs_compaction(self._messages):
                self._messages = await context_manager.compact(self._messages)
                logger.debug("context_compacted", agent_id=self.id)
        except Exception:
            pass

    # ─── Memory (Optimized) ─────────────────────────────────────

    async def _recall_context(self, query: str) -> str:
        """Recall relevant documents from ChromaDB (with timeout)."""
        try:
            from memory.vector_store import vector_store
            results = await asyncio.wait_for(
                vector_store.query(collection="agent_memory", query_text=query, n_results=3),
                timeout=5.0,
            )
            if results:
                return "\n---\nRelevant memory:\n" + "\n".join(
                    r.get("document", "")[:300] for r in results if r.get("document")
                )
        except (asyncio.TimeoutError, Exception):
            pass
        return ""

    async def _recall_learned_patterns(self, query: str) -> str:
        """Recall learned patterns from skill library."""
        try:
            from services.skill_library import skill_library
            skills = await skill_library.find_similar_skills(query, limit=2)
            if skills:
                return "\n---\nRelevant learned patterns:\n" + "\n".join(
                    f"- {s['name']}: {s['description']}" for s in skills
                )
        except Exception:
            pass
        return ""

    async def _post_completion(self, task: str, result: str, duration: float):
        """Post-completion tasks (run async, don't block response)."""
        try:
            # Store in vector memory
            from memory.vector_store import vector_store
            await vector_store.add_documents(
                collection="agent_memory",
                documents=[f"Task: {task[:200]}\nResult: {result[:300]}"],
                metadatas=[{"agent_id": self.id, "role": self.role.value, "duration": duration}],
                ids=[f"mem_{self.id}_{uuid.uuid4().hex[:8]}"],
            )
        except Exception:
            pass

        try:
            # Post to message bus
            from agents.message_bus import message_bus
            await message_bus.publish(
                topic=f"agent.{self.role.value}.completed",
                data={
                    "agent_id": self.id,
                    "role": self.role.value,
                    "task": task[:200],
                    "result": result[:300],
                    "duration_s": round(duration, 2),
                    "tokens": self._total_tokens_used,
                },
            )
        except Exception:
            pass

    async def _track_tokens_async(self, response_data: dict):
        """Track token usage (async, non-blocking)."""
        try:
            from services.token_tracker import token_tracker
            await token_tracker.record(
                agent_id=self.id,
                agent_role=self.role.value,
                model=self.model,
                prompt_tokens=response_data.get("prompt_eval_count", 0),
                completion_tokens=response_data.get("eval_count", 0),
                playbook_id=self.playbook_id,
            )
        except Exception:
            pass

    # ─── Enriched System Prompt ─────────────────────────────────

    def _build_enriched_system_prompt(
        self,
        relevant_context: str = "",
        learned_context: str = "",
        extra_context: Dict[str, Any] = None,
    ) -> str:
        """Build the fully-enriched system prompt with all augmentations."""
        parts = [self.system_prompt()]

        # Identity
        parts.append(f"\nYou are '{self.name}' (role: {self.role.value}), part of MiLyfe Brain agent swarm.")

        # Tool instructions
        parts.append(
            "You have access to tools. To use a tool, output JSON:\n"
            '{"tool": "tool_name", "args": {"param": "value"}}\n'
            "You can call multiple tools per response. After tool results, continue reasoning."
        )

        # Available tools list
        try:
            from tools.registry import tool_registry
            parts.append(tool_registry.list_tools_for_prompt())
        except Exception:
            pass

        # Rules (hierarchical .rules files)
        try:
            from prompts.rule_loader import rule_loader
            rules = rule_loader.get_rules_for_prompt(role=self.role.value)
            if rules:
                parts.append(rules)
        except Exception:
            pass

        # Semantic skills (auto-activated by input)
        try:
            from services.semantic_skills import semantic_skills
            task_text = extra_context.get("task", self.task) if extra_context else self.task
            active = semantic_skills.get_active_skills(task_text)
            if active:
                instructions = semantic_skills.get_skill_instructions(active)
                if instructions:
                    parts.append(f"\n[Active Skills]\n{instructions}")
        except Exception:
            pass

        # Environment snapshot
        try:
            from services.env_snapshot import env_snapshot
            env_ctx = env_snapshot.get_for_prompt()
            if env_ctx:
                parts.append(env_ctx)
        except Exception:
            pass

        # Scratchpad (short-term working memory)
        try:
            from tools.scratchpad_tools import get_scratchpad_context
            session_id = extra_context.get("session_id", "default") if extra_context else "default"
            scratch = get_scratchpad_context(session_id)
            if scratch:
                parts.append(scratch)
        except Exception:
            pass

        # Learned corrections (if any)
        if self._corrections:
            parts.append("\n[User Corrections — Always follow these]\n" +
                        "\n".join(f"- {c}" for c in self._corrections[-5:]))

        # Vector memory context
        if relevant_context:
            parts.append(relevant_context)

        # Learned patterns
        if learned_context:
            parts.append(learned_context)

        # Extra context from caller
        if extra_context:
            ctx_items = [(k, v) for k, v in extra_context.items()
                        if v and k not in ("session_id", "task")]
            if ctx_items:
                parts.append("\n[Context]\n" + "\n".join(f"- {k}: {v}" for k, v in ctx_items))

        return "\n\n".join(parts)

    def _format_tool_results(self, results: List[ToolResult]) -> str:
        """Format tool results for feeding back to LLM."""
        parts = []
        for r in results:
            if r.success:
                output = r.output[:2000] if r.output else "(no output)"
                parts.append(f"[{r.tool_name}] SUCCESS ({r.execution_time_ms:.0f}ms):\n{output}")
            else:
                parts.append(f"[{r.tool_name}] FAILED: {r.error}")
        return "\n\n".join(parts)

    def _emit_event(self, event_type: EventType, data: dict):
        """Emit a stream event."""
        try:
            from api.routes.streaming import emit_event
            emit_event(
                event_type=event_type,
                agent_id=self.id,
                agent_role=self.role.value,
                data=data,
                playbook_id=self.playbook_id,
            )
        except Exception:
            pass

    def _default_model(self) -> str:
        """Get default model for this role's complexity."""
        heavy_roles = {AgentRole.CODER, AgentRole.EXECUTOR, AgentRole.CRITIC, AgentRole.DEBUGGER}
        if self.role in heavy_roles:
            return settings.default_heavy_model
        return settings.default_light_model

    def _role_name(self) -> str:
        names = {
            AgentRole.ORCHESTRATOR: "Conductor",
            AgentRole.RESEARCHER: "Explorer",
            AgentRole.CODER: "Builder",
            AgentRole.EXECUTOR: "Runner",
            AgentRole.CRITIC: "Judge",
            AgentRole.DESIGNER: "Architect",
            AgentRole.WRITER: "Scribe",
            AgentRole.DEBUGGER: "Detective",
            AgentRole.PLANNER: "Strategist",
        }
        return names.get(self.role, "Agent")

    def _avatar_color(self) -> str:
        colors = {
            AgentRole.ORCHESTRATOR: "#f59e0b",
            AgentRole.RESEARCHER: "#06b6d4",
            AgentRole.CODER: "#8b5cf6",
            AgentRole.EXECUTOR: "#ef4444",
            AgentRole.CRITIC: "#f97316",
            AgentRole.DESIGNER: "#ec4899",
            AgentRole.WRITER: "#14b8a6",
            AgentRole.DEBUGGER: "#6366f1",
            AgentRole.PLANNER: "#10b981",
        }
        return colors.get(self.role, "#5c7cfa")
