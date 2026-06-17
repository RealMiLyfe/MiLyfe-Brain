"""MiLyfe Brain — BaseAgent ABC (think/act loop, httpx → Ollama)."""

from __future__ import annotations

import abc
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

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


class BaseAgent(abc.ABC):
    """Abstract base class for all MiLyfe Brain agents.

    Implements the think/act loop:
    1. Build system prompt (role + rules + skills + style + env)
    2. Call Ollama /api/chat via httpx
    3. Parse response for tool calls
    4. Execute tools (with hooks)
    5. Feed results back, repeat up to max_rounds
    6. Store results in vector memory
    7. Post to message bus
    """

    def __init__(
        self,
        role: AgentRole,
        agent_id: Optional[str] = None,
        model: Optional[str] = None,
        task: str = "",
    ):
        self.id = agent_id or str(uuid.uuid4())
        self.role = role
        self.model = model or self._default_model()
        self.task = task
        self.name = self._role_name()
        self.avatar_color = self._avatar_color()

        self._messages: List[Dict[str, str]] = []
        self._thoughts: List[str] = []
        self._actions_taken: int = 0
        self._progress: float = 0.0
        self._spawned_at = datetime.utcnow()

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
            thoughts=self._thoughts[-5:],  # Last 5 thoughts
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
    ) -> str:
        """Execute the think/act loop for a task.

        Returns the final response text.
        """
        self.task = task
        context = context or {}
        start_time = time.time()

        # 1. Recall relevant docs from vector memory
        relevant_context = await self._recall_context(task)

        # 2. Build system prompt
        system = self._build_full_system_prompt(relevant_context, context)

        # 3. Initialize message history for this task
        self._messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": task},
        ]

        # Emit spawned event
        self._emit_event(EventType.AGENT_SPAWNED, {"task": task[:200]})

        # 4-7. Tool loop
        final_response = ""
        for round_num in range(max_rounds):
            # Call Ollama
            response_text = await self._call_llm()

            if not response_text:
                final_response = "No response generated."
                break

            # Record thought
            self._thoughts.append(response_text[:200])
            self._emit_event(EventType.THOUGHT, {"content": response_text[:500], "round": round_num})

            # Parse tool calls
            from agents.tool_parser import parse_tool_calls
            tool_calls = parse_tool_calls(response_text)

            if not tool_calls:
                # No tool calls — this is the final response
                final_response = response_text
                break

            # Execute tools
            tool_results = await self._execute_tools(tool_calls)

            # Feed results back to LLM
            tool_output = self._format_tool_results(tool_results)
            self._messages.append({"role": "assistant", "content": response_text})
            self._messages.append({"role": "user", "content": f"Tool results:\n{tool_output}"})

            self._progress = (round_num + 1) / max_rounds

        # 8. Store result in vector memory
        await self._store_memory(task, final_response)

        # 9. Post to message bus
        await self._post_to_bus(task, final_response)

        self._emit_event(EventType.COMPLETED, {
            "response_length": len(final_response),
            "rounds": min(max_rounds, len(self._thoughts)),
            "duration_s": round(time.time() - start_time, 2),
        })

        self._progress = 1.0
        return final_response

    # ─── LLM Interaction ────────────────────────────────────────

    async def _call_llm(self) -> str:
        """Call Ollama /api/chat via httpx (pure, no langchain)."""
        try:
            async with httpx.AsyncClient(timeout=settings.agent_timeout) as client:
                resp = await client.post(
                    f"{settings.ollama_base_url}/api/chat",
                    json={
                        "model": self.model,
                        "messages": self._messages,
                        "stream": False,
                        "options": {
                            "temperature": 0.7,
                            "num_predict": 4096,
                        },
                    },
                )

                if resp.status_code != 200:
                    logger.error("llm_call_failed", status=resp.status_code, body=resp.text[:200])
                    return ""

                data = resp.json()
                content = data.get("message", {}).get("content", "")

                # Track tokens
                await self._track_tokens(data)

                return content

        except httpx.TimeoutException:
            logger.error("llm_timeout", model=self.model, agent_id=self.id)
            return ""
        except Exception as e:
            logger.error("llm_error", error=str(e), model=self.model)
            return ""

    # ─── Tool Execution ─────────────────────────────────────────

    async def _execute_tools(self, tool_calls: List[ToolCall]) -> List[ToolResult]:
        """Execute tool calls with pre/post hooks."""
        results = []
        for tc in tool_calls:
            self._actions_taken += 1
            self._emit_event(EventType.TOOL_CALL, {"tool": tc.tool_name, "args": tc.arguments})

            try:
                # Pre-hooks
                from hooks.registry import hook_registry
                tc = await hook_registry.run_pre_hooks(tc, self)

                # Execute
                from tools.registry import tool_registry
                result = await tool_registry.execute(tc.tool_name, tc.arguments, agent=self)

                # Post-hooks
                result = await hook_registry.run_post_hooks(result, self)

                results.append(result)
                self._emit_event(EventType.TOOL_RESULT, {
                    "tool": tc.tool_name,
                    "success": result.success,
                    "output_preview": result.output[:200] if result.output else "",
                })

            except Exception as e:
                results.append(ToolResult(
                    tool_name=tc.tool_name,
                    success=False,
                    error=str(e),
                ))
                logger.error("tool_execution_failed", tool=tc.tool_name, error=str(e))

        return results

    # ─── Memory ─────────────────────────────────────────────────

    async def _recall_context(self, query: str) -> str:
        """Recall relevant documents from ChromaDB."""
        try:
            from memory.vector_store import vector_store
            results = await vector_store.query(
                collection="agent_memory",
                query_text=query,
                n_results=3,
            )
            if results:
                return "\n---\nRelevant context:\n" + "\n".join(
                    r.get("document", "") for r in results
                )
        except Exception:
            pass
        return ""

    async def _store_memory(self, task: str, result: str):
        """Store result in vector memory for future recall."""
        try:
            from memory.vector_store import vector_store
            await vector_store.add_documents(
                collection="agent_memory",
                documents=[f"Task: {task}\nResult: {result[:500]}"],
                metadatas=[{"agent_id": self.id, "role": self.role.value}],
                ids=[f"mem_{self.id}_{uuid.uuid4().hex[:8]}"],
            )
        except Exception:
            pass  # Non-critical

    async def _post_to_bus(self, task: str, result: str):
        """Post result to inter-agent message bus."""
        try:
            from agents.message_bus import message_bus
            await message_bus.publish(
                topic=f"agent.{self.role.value}.completed",
                data={
                    "agent_id": self.id,
                    "role": self.role.value,
                    "task": task[:200],
                    "result": result[:500],
                },
            )
        except Exception:
            pass

    # ─── Token Tracking ─────────────────────────────────────────

    async def _track_tokens(self, response_data: dict):
        """Track token usage."""
        try:
            prompt_tokens = response_data.get("prompt_eval_count", 0)
            completion_tokens = response_data.get("eval_count", 0)

            from services.token_tracker import token_tracker
            await token_tracker.record(
                agent_id=self.id,
                agent_role=self.role.value,
                model=self.model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
            )
        except Exception:
            pass

    # ─── Helpers ────────────────────────────────────────────────

    def _build_full_system_prompt(self, relevant_context: str, extra_context: Dict[str, Any]) -> str:
        """Build the full system prompt with all augmentations."""
        parts = [self.system_prompt()]

        # Add role-specific instructions
        parts.append(f"\nYou are '{self.name}' (role: {self.role.value}).")
        parts.append("You have access to tools. Use them when needed.")
        parts.append("Format tool calls as JSON: {\"tool\": \"name\", \"args\": {...}}")

        # Add relevant context from memory
        if relevant_context:
            parts.append(relevant_context)

        # Add extra context
        if extra_context:
            ctx_str = "\n".join(f"- {k}: {v}" for k, v in extra_context.items() if v)
            if ctx_str:
                parts.append(f"\nAdditional context:\n{ctx_str}")

        return "\n\n".join(parts)

    def _format_tool_results(self, results: List[ToolResult]) -> str:
        """Format tool results for feeding back to LLM."""
        parts = []
        for r in results:
            if r.success:
                parts.append(f"[{r.tool_name}] SUCCESS:\n{r.output[:2000]}")
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
        """Human-friendly name for this role."""
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
        """Color for UI avatar."""
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
