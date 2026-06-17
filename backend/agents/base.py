"""
MiLyfe Brain - Base Agent

Abstract base class for all specialized agents. Provides LLM calling, tool execution,
context management, and event emission capabilities.
"""
from __future__ import annotations

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, AsyncGenerator, Dict, List, Optional
from uuid import uuid4

import httpx

from config import settings
from models.schemas import (
    AgentRole,
    AgentState,
    OutputStyle,
    TaskStatus,
    ToolCall,
    ToolResult,
    TopicType,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Shared connection pool (module-level singleton)
# ---------------------------------------------------------------------------

_http_pool: Optional[httpx.AsyncClient] = None


async def get_http_pool() -> httpx.AsyncClient:
    """Get or create the shared httpx async connection pool."""
    global _http_pool
    if _http_pool is None or _http_pool.is_closed:
        _http_pool = httpx.AsyncClient(
            base_url=settings.ollama_base_url,
            timeout=httpx.Timeout(connect=10.0, read=300.0, write=30.0, pool=10.0),
            limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
        )
    return _http_pool


# ---------------------------------------------------------------------------
# BaseAgent ABC
# ---------------------------------------------------------------------------


class BaseAgent(ABC):
    """
    Abstract base class for all MiLyfe Brain agents.

    Provides:
    - LLM calling with connection pooling and circuit breaker
    - Tool execution (parallel when safe, sequential on conflicts)
    - Context management and memory recall
    - Event emission to the message bus
    """

    def __init__(
        self,
        role: AgentRole,
        task: str,
        agent_id: Optional[str] = None,
        model: Optional[str] = None,
        playbook_id: Optional[str] = None,
    ) -> None:
        self.id: str = agent_id or str(uuid4())
        self.role: AgentRole = role
        self.model: str = model or self._default_model()
        self.task: str = task
        self.playbook_id: Optional[str] = playbook_id
        self.name: str = self._role_name()
        self.avatar_color: str = self._avatar_color()

        # Internal state
        self._messages: List[Dict[str, Any]] = []
        self._thoughts: List[str] = []
        self._actions_taken: int = 0
        self._progress: float = 0.0
        self._spawned_at: datetime = datetime.utcnow()
        self._total_tokens_used: int = 0
        self._total_duration_ms: float = 0.0
        self._corrections: List[str] = []

    # ------------------------------------------------------------------
    # Abstract
    # ------------------------------------------------------------------

    @abstractmethod
    def system_prompt(self) -> str:
        """Return the role-specific system prompt."""
        ...

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_state(self) -> AgentState:
        """Return current agent state as a serializable model."""
        return AgentState(
            id=self.id,
            role=self.role,
            status=TaskStatus.RUNNING if self._actions_taken > 0 else TaskStatus.PENDING,
            current_task=self.task,
            playbook_id=self.playbook_id,
            thinking=self._thoughts[-1] if self._thoughts else None,
            last_action=None,
            tokens_used=self._total_tokens_used,
            started_at=self._spawned_at,
            model=self.model,
        )

    async def think(
        self,
        task: str,
        context: Optional[Dict[str, Any]] = None,
        max_rounds: int = 3,
        stream: bool = False,
    ) -> str:
        """
        High-level reasoning method. Delegates to the TAOR engine for
        multi-turn think-act-observe-repeat execution.
        """
        try:
            from taor_engine import TAOREngine

            engine = TAOREngine()
            result = await engine.execute(
                agent=self,
                task=task,
                context=context,
                max_turns=max_rounds,
                stream=stream,
            )
            return result
        except Exception as e:
            logger.error(f"Agent {self.id} think error: {e}")
            return f"Error during reasoning: {e}"

    async def think_streaming(
        self,
        task: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> AsyncGenerator[str, None]:
        """Stream tokens from Ollama for real-time output."""
        self._messages.append({"role": "user", "content": task})

        system = self._build_enriched_system_prompt(
            relevant_context=await self._recall_context(task),
            learned_context=await self._recall_learned_patterns(task),
            extra_context=context.get("extra", "") if context else "",
        )

        payload = {
            "model": self.model,
            "messages": [{"role": "system", "content": system}] + self._messages,
            "stream": True,
        }

        pool = await get_http_pool()
        full_response = ""

        try:
            async with pool.stream("POST", "/api/chat", json=payload) as response:
                response.raise_for_status()
                import json as json_mod

                async for line in response.aiter_lines():
                    if not line.strip():
                        continue
                    try:
                        chunk = json_mod.loads(line)
                        token = chunk.get("message", {}).get("content", "")
                        if token:
                            full_response += token
                            yield token
                        if chunk.get("done", False):
                            # Track tokens from final chunk
                            asyncio.create_task(self._track_tokens_async(chunk))
                            break
                    except (json_mod.JSONDecodeError, KeyError):
                        continue
        except httpx.HTTPError as e:
            logger.error(f"Streaming error: {e}")
            yield f"\n[Error: {e}]"

        self._messages.append({"role": "assistant", "content": full_response})

    def record_correction(self, correction: str) -> None:
        """Record an external correction for learning purposes."""
        self._corrections.append(correction)
        self._thoughts.append(f"[Correction received]: {correction}")

    # ------------------------------------------------------------------
    # Private: LLM Calling
    # ------------------------------------------------------------------

    async def _call_llm_safe(self) -> str:
        """Call LLM with circuit breaker fallback."""
        try:
            return await self._call_llm_pooled()
        except Exception as e:
            logger.warning(f"Primary LLM call failed: {e}, trying fallback")
            try:
                return await self._call_llm_fallback()
            except Exception as fallback_err:
                logger.error(f"All LLM calls failed: {fallback_err}")
                return f"[LLM unavailable: {e}]"

    async def _call_llm_pooled(self) -> str:
        """Call Ollama /api/chat using shared httpx connection pool."""
        pool = await get_http_pool()

        payload = {
            "model": self.model,
            "messages": self._messages,
            "stream": False,
        }

        start = time.perf_counter()
        response = await pool.post("/api/chat", json=payload)
        response.raise_for_status()
        elapsed_ms = (time.perf_counter() - start) * 1000
        self._total_duration_ms += elapsed_ms

        data = response.json()
        content = data.get("message", {}).get("content", "")

        # Track tokens asynchronously
        asyncio.create_task(self._track_tokens_async(data))

        return content

    async def _call_llm_fallback(self) -> str:
        """Try fallback model via model_fallback service."""
        try:
            from services.model_fallback import get_fallback_response

            return await get_fallback_response(
                messages=self._messages,
                primary_model=self.model,
            )
        except ImportError:
            # Fallback to light model directly
            pool = await get_http_pool()
            payload = {
                "model": settings.default_light_model,
                "messages": self._messages,
                "stream": False,
            }
            response = await pool.post("/api/chat", json=payload)
            response.raise_for_status()
            data = response.json()
            return data.get("message", {}).get("content", "")

    # ------------------------------------------------------------------
    # Private: Tool Execution
    # ------------------------------------------------------------------

    async def _execute_tools_optimized(self, tool_calls: List[ToolCall]) -> List[ToolResult]:
        """Execute tool calls in parallel if safe, sequential if file conflicts."""
        if not tool_calls:
            return []

        if self._can_parallelize(tool_calls):
            tasks = [self._execute_single_tool(tc) for tc in tool_calls]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            return [
                r if isinstance(r, ToolResult) else ToolResult(
                    tool_call_id=tool_calls[i].id,
                    success=False,
                    error=str(r),
                )
                for i, r in enumerate(results)
            ]
        else:
            results: List[ToolResult] = []
            for tc in tool_calls:
                result = await self._execute_single_tool(tc)
                results.append(result)
            return results

    async def _execute_single_tool(self, tc: ToolCall) -> ToolResult:
        """Execute a single tool call with hooks and registry."""
        start = time.perf_counter()
        try:
            from services.tool_registry import get_tool_registry

            registry = get_tool_registry()
            result = await registry.execute(tc)
            elapsed = (time.perf_counter() - start) * 1000
            result.duration_ms = elapsed
            self._actions_taken += 1
            return result
        except ImportError:
            elapsed = (time.perf_counter() - start) * 1000
            return ToolResult(
                tool_call_id=tc.id,
                success=False,
                error="Tool registry not available",
                duration_ms=elapsed,
            )
        except Exception as e:
            elapsed = (time.perf_counter() - start) * 1000
            return ToolResult(
                tool_call_id=tc.id,
                success=False,
                error=str(e),
                duration_ms=elapsed,
            )

    def _can_parallelize(self, tool_calls: List[ToolCall]) -> bool:
        """Check if tool calls can safely run in parallel (no file path conflicts)."""
        file_paths: List[str] = []
        for tc in tool_calls:
            path = tc.arguments.get("path") or tc.arguments.get("file_path") or ""
            if path:
                if path in file_paths:
                    return False
                file_paths.append(path)
        return True

    # ------------------------------------------------------------------
    # Private: Context Management
    # ------------------------------------------------------------------

    async def _maybe_compact_context(self) -> None:
        """Check if context needs compaction and trigger if necessary."""
        try:
            from services.context_manager import get_context_manager

            cm = get_context_manager()
            if cm.needs_compaction(self._messages):
                self._messages = await cm.compact(self._messages, self.model)
        except ImportError:
            # Context manager not available, use simple truncation
            threshold = settings.context_summarize_threshold
            estimated = sum(len(m.get("content", "")) for m in self._messages) // 4
            if estimated > threshold:
                # Keep system + last 10 messages
                if len(self._messages) > 12:
                    self._messages = self._messages[:1] + self._messages[-10:]

    async def _recall_context(self, query: str) -> str:
        """Recall relevant context from ChromaDB with 5s timeout."""
        try:
            from services.memory_service import recall_memories

            result = await asyncio.wait_for(
                recall_memories(query=query, agent_role=self.role),
                timeout=5.0,
            )
            return result if result else ""
        except (ImportError, asyncio.TimeoutError, Exception) as e:
            logger.debug(f"Context recall skipped: {e}")
            return ""

    async def _recall_learned_patterns(self, query: str) -> str:
        """Recall learned patterns from the skill library."""
        try:
            from services.skill_library import get_skill_library

            library = get_skill_library()
            skills = await asyncio.wait_for(
                library.find_similar_skills(query, limit=3),
                timeout=5.0,
            )
            if skills:
                return "\n".join(f"- {s}" for s in skills)
            return ""
        except (ImportError, asyncio.TimeoutError, Exception) as e:
            logger.debug(f"Pattern recall skipped: {e}")
            return ""

    # ------------------------------------------------------------------
    # Private: Post-Completion
    # ------------------------------------------------------------------

    async def _post_completion(self, task: str, result: str, duration: float) -> None:
        """Fire-and-forget: store memory + post to message bus."""
        try:
            # Store memory
            try:
                from services.memory_service import store_memory

                await store_memory(
                    content=f"Task: {task}\nResult: {result[:500]}",
                    agent_role=self.role,
                    playbook_id=self.playbook_id,
                )
            except ImportError:
                pass

            # Publish to bus
            try:
                from agents.message_bus import MessageBus

                bus = MessageBus()
                await bus.publish(
                    topic=f"agent.{self.role.value}.completed",
                    data={
                        "agent_id": self.id,
                        "task": task,
                        "duration_ms": duration,
                        "tokens": self._total_tokens_used,
                    },
                )
            except ImportError:
                pass
        except Exception as e:
            logger.debug(f"Post-completion error (non-fatal): {e}")

    async def _track_tokens_async(self, response_data: Dict[str, Any]) -> None:
        """Asynchronously track token usage from Ollama response."""
        try:
            prompt_tokens = response_data.get("prompt_eval_count", 0)
            completion_tokens = response_data.get("eval_count", 0)
            total = prompt_tokens + completion_tokens
            self._total_tokens_used += total
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Private: Prompt Building
    # ------------------------------------------------------------------

    def _build_enriched_system_prompt(
        self,
        relevant_context: str,
        learned_context: str,
        extra_context: str,
    ) -> str:
        """
        Build a 9-layer enriched system prompt:
        1. Base system prompt (role-specific)
        2. Identity layer
        3. Available tools list
        4. Rules & constraints
        5. Environment snapshot
        6. Skills / learned patterns
        7. Scratchpad / working memory
        8. Project intelligence
        9. Learning context (memory recall)
        """
        layers: List[str] = []

        # Layer 1: Base prompt
        layers.append(self.system_prompt())

        # Layer 2: Identity
        layers.append(
            f"\n[Identity] You are {self.name} (role={self.role.value}, id={self.id}). "
            f"Model: {self.model}."
        )

        # Layer 3: Tools list
        try:
            from services.tool_registry import get_tool_registry

            registry = get_tool_registry()
            tool_names = registry.list_tool_names(role=self.role)
            if tool_names:
                layers.append(f"\n[Available Tools] {', '.join(tool_names)}")
        except (ImportError, Exception):
            pass

        # Layer 4: Rules
        layers.append(
            "\n[Rules] "
            "- Always explain reasoning before acting. "
            "- Use tools when you need information or to perform actions. "
            "- Stop and report if uncertain about destructive operations. "
            "- Keep responses focused and relevant to the task."
        )

        # Layer 5: Environment snapshot
        layers.append(
            f"\n[Environment] Workspace: {settings.workspace_dir} | "
            f"Max tool rounds: {settings.max_tool_rounds}"
        )

        # Layer 6: Skills / learned patterns
        if learned_context:
            layers.append(f"\n[Learned Patterns]\n{learned_context}")

        # Layer 7: Scratchpad
        if self._thoughts:
            recent_thoughts = self._thoughts[-5:]
            layers.append(
                f"\n[Scratchpad]\n" + "\n".join(f"- {t}" for t in recent_thoughts)
            )

        # Layer 8: Project intelligence
        if extra_context:
            layers.append(f"\n[Project Context]\n{extra_context}")

        # Layer 9: Learning context (memory recall)
        if relevant_context:
            layers.append(f"\n[Relevant Memory]\n{relevant_context}")

        return "\n".join(layers)

    # ------------------------------------------------------------------
    # Private: Utilities
    # ------------------------------------------------------------------

    def _format_tool_results(self, results: List[ToolResult]) -> str:
        """Format tool results into a readable string for the LLM."""
        parts: List[str] = []
        for r in results:
            if r.success:
                parts.append(f"[Tool OK] {r.output or 'Done'}")
            else:
                parts.append(f"[Tool ERROR] {r.error or 'Unknown error'}")
        return "\n".join(parts)

    async def _emit_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Emit an event to the message bus."""
        try:
            from agents.message_bus import MessageBus

            bus = MessageBus()
            await bus.publish(
                topic=f"agent.{self.role.value}.{event_type}",
                data={"agent_id": self.id, **data},
            )
        except (ImportError, Exception) as e:
            logger.debug(f"Event emission skipped: {e}")

    def _default_model(self) -> str:
        """Heavy roles get heavy model, light roles get light model."""
        heavy_roles = {
            AgentRole.ORCHESTRATOR,
            AgentRole.CODER,
            AgentRole.PLANNER,
            AgentRole.REVIEWER,
        }
        if self.role in heavy_roles:
            return settings.default_heavy_model
        return settings.default_light_model

    def _role_name(self) -> str:
        """Map role enum to a human-friendly name."""
        names: Dict[AgentRole, str] = {
            AgentRole.ORCHESTRATOR: "Conductor",
            AgentRole.RESEARCHER: "Explorer",
            AgentRole.CODER: "Builder",
            AgentRole.EXECUTOR: "Runner",
            AgentRole.REVIEWER: "Judge",
            AgentRole.PLANNER: "Strategist",
            AgentRole.WRITER: "Scribe",
            AgentRole.BROWSER: "Navigator",
            AgentRole.GUI: "Interface",
        }
        return names.get(self.role, self.role.value.capitalize())

    def _avatar_color(self) -> str:
        """Map role to a hex color for UI avatars."""
        colors: Dict[AgentRole, str] = {
            AgentRole.ORCHESTRATOR: "#6366F1",  # Indigo
            AgentRole.RESEARCHER: "#10B981",    # Emerald
            AgentRole.CODER: "#F59E0B",         # Amber
            AgentRole.EXECUTOR: "#EF4444",      # Red
            AgentRole.REVIEWER: "#8B5CF6",      # Purple
            AgentRole.PLANNER: "#3B82F6",       # Blue
            AgentRole.WRITER: "#EC4899",        # Pink
            AgentRole.BROWSER: "#14B8A6",       # Teal
            AgentRole.GUI: "#F97316",           # Orange
        }
        return colors.get(self.role, "#6B7280")
