"""
MiLyfe Brain - TAOR Engine

Think-Act-Observe-Repeat execution engine for agents.
Manages the multi-turn reasoning loop with tool execution, safety checks,
context compaction, sub-agent dispatch, and memory persistence.
"""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, TYPE_CHECKING

from models.schemas import (
    AgentRole,
    OutputStyle,
    ToolCall,
    ToolResult,
    TopicType,
)

if TYPE_CHECKING:
    from agents.base import BaseAgent

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data Structures
# ---------------------------------------------------------------------------


@dataclass
class PromptLayer:
    """A named layer in the multi-layer prompt system."""

    name: str
    priority: int
    content_fn: Callable[[], str]
    active: bool = True


# ---------------------------------------------------------------------------
# TAOREngine Singleton
# ---------------------------------------------------------------------------


class TAOREngine:
    """
    Think-Act-Observe-Repeat engine.

    Orchestrates the full agent reasoning loop:
    1. Detect topic type
    2. Build multi-layer enriched prompt
    3. TAOR loop: LLM call → parse tools → execute safely → observe → repeat
    4. Post-completion: persist memory, publish events, record learning
    """

    _instance: Optional[TAOREngine] = None

    def __new__(cls) -> TAOREngine:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    # ------------------------------------------------------------------
    # Main Execution
    # ------------------------------------------------------------------

    async def execute(
        self,
        agent: BaseAgent,
        task: str,
        context: Optional[Dict[str, Any]] = None,
        max_turns: int = 10,
        output_style: Optional[OutputStyle] = None,
        stream: bool = False,
    ) -> str:
        """
        Execute the full TAOR loop for a given agent and task.

        Args:
            agent: The agent performing the task
            task: The task description / user message
            context: Optional additional context dict
            max_turns: Maximum number of TAOR iterations
            output_style: Desired output formatting
            stream: Whether to stream (currently returns final result)

        Returns:
            Final response string from the agent
        """
        start_time = time.perf_counter()
        context = context or {}

        # Step 1: Detect topic
        topic_type = self._detect_topic(task, context)

        # Step 2: Build layered system prompt
        system_prompt = await self._build_layered_prompt(
            agent=agent,
            task=task,
            context=context,
            output_style=output_style,
        )

        # Initialize message history for this execution
        agent._messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": task},
        ]

        final_response = ""
        turns = 0

        # Step 3: TAOR Loop
        while turns < max_turns:
            turns += 1

            # Think: call LLM
            try:
                response = await agent._call_llm_safe()
            except Exception as e:
                logger.error(f"TAOR LLM call failed on turn {turns}: {e}")
                final_response = f"Error during reasoning (turn {turns}): {e}"
                break

            if not response:
                final_response = "[No response from model]"
                break

            agent._messages.append({"role": "assistant", "content": response})
            agent._thoughts.append(response[:200])

            # Act: parse tool calls
            try:
                from agents.tool_parser import parse_tool_calls

                tool_calls = parse_tool_calls(response)
            except ImportError:
                tool_calls = []
            except Exception as e:
                logger.warning(f"Tool parsing error: {e}")
                tool_calls = []

            # If no tools, this is the final response
            if not tool_calls:
                final_response = response
                break

            # Execute tools with safety
            results = await self._execute_tools_with_safety(
                tool_calls=tool_calls,
                agent=agent,
                context=context,
            )

            # Observe: format observations and inject into messages
            observations = self._format_observations(results)
            post_hook = self._get_post_hook_content(results, agent)

            observation_msg = observations
            if post_hook:
                observation_msg += f"\n\n{post_hook}"

            agent._messages.append({"role": "user", "content": observation_msg})

            # Check context compaction
            if self._needs_compaction(agent._messages):
                agent._messages = await self._compact_context(agent._messages, agent)

            # Check if we should dispatch a sub-agent
            if self._should_dispatch_subagent(response, results):
                sub_result = await self._dispatch_subagent(
                    parent_agent=agent,
                    response=response,
                    results=results,
                    context=context,
                )
                if sub_result:
                    agent._messages.append(
                        {"role": "user", "content": f"[Sub-agent result]: {sub_result}"}
                    )

        # Step 4: Post-completion (fire-and-forget)
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        asyncio.create_task(
            agent._post_completion(task=task, result=final_response, duration=elapsed_ms)
        )

        # Step 5: Record success/failure in agent learning
        self._record_outcome(agent, task, final_response, elapsed_ms, success=bool(final_response))

        return final_response

    # ------------------------------------------------------------------
    # Topic Detection
    # ------------------------------------------------------------------

    def _detect_topic(self, text: str, context: Dict[str, Any]) -> TopicType:
        """Detect the topic type from task text and context."""
        try:
            from services.topic_detector import detect_topic

            return detect_topic(text)
        except ImportError:
            # Fallback: simple keyword-based detection
            text_lower = text.lower()

            if any(kw in text_lower for kw in ("bug", "error", "fix", "debug", "traceback", "exception")):
                return TopicType.DEBUGGING
            elif any(kw in text_lower for kw in ("write code", "implement", "function", "class", "api")):
                return TopicType.CODING
            elif any(kw in text_lower for kw in ("search", "find", "look up", "research", "documentation")):
                return TopicType.RESEARCH
            elif any(kw in text_lower for kw in ("write", "document", "readme", "report", "article")):
                return TopicType.WRITING
            elif any(kw in text_lower for kw in ("plan", "design", "architect", "roadmap", "strategy")):
                return TopicType.PLANNING
            elif any(kw in text_lower for kw in ("brainstorm", "ideas", "creative", "suggest")):
                return TopicType.BRAINSTORMING
            elif any(kw in text_lower for kw in ("analyze", "compare", "evaluate", "assess")):
                return TopicType.ANALYSIS
            else:
                return TopicType.GENERAL

    # ------------------------------------------------------------------
    # Prompt Building
    # ------------------------------------------------------------------

    async def _build_layered_prompt(
        self,
        agent: BaseAgent,
        task: str,
        context: Dict[str, Any],
        output_style: Optional[OutputStyle] = None,
    ) -> str:
        """
        Build the 9-layer enriched system prompt.

        Layers:
        1. Base system prompt (role-specific)
        2. Identity
        3. Tools list
        4. Rules & constraints
        5. Environment snapshot
        6. Skills / learned patterns
        7. Scratchpad
        8. Project intelligence
        9. Learning context (memory recall)
        """
        # Fetch memory layers in parallel
        memory_context, learning_context = await self._fetch_memory_layers(agent, task)

        extra_context = context.get("extra", "")

        # Add output style instruction if specified
        style_instruction = ""
        if output_style:
            style_map = {
                OutputStyle.CONCISE: "Be brief and to the point. No unnecessary elaboration.",
                OutputStyle.DETAILED: "Provide thorough, detailed explanations.",
                OutputStyle.MARKDOWN: "Format your response in clean Markdown.",
                OutputStyle.CODE_ONLY: "Respond with code only. No explanations unless critical.",
                OutputStyle.STEP_BY_STEP: "Break your response into numbered steps.",
                OutputStyle.BULLET_POINTS: "Use bullet points for key information.",
                OutputStyle.CONVERSATIONAL: "Be friendly and conversational in tone.",
                OutputStyle.TECHNICAL: "Use precise technical language for a developer audience.",
            }
            style_instruction = style_map.get(output_style, "")

        combined_extra = f"{extra_context}\n{style_instruction}".strip() if style_instruction else extra_context

        return agent._build_enriched_system_prompt(
            relevant_context=memory_context,
            learned_context=learning_context,
            extra_context=combined_extra,
        )

    async def _fetch_memory_layers(self, agent: BaseAgent, task: str) -> tuple:
        """Gather memory and learning context in parallel."""
        memory_task = asyncio.create_task(agent._recall_context(task))
        learning_task = asyncio.create_task(self._get_learning_context(agent, task))

        try:
            memory_context, learning_context = await asyncio.gather(
                memory_task, learning_task, return_exceptions=True
            )
        except Exception:
            memory_context = ""
            learning_context = ""

        if isinstance(memory_context, Exception):
            memory_context = ""
        if isinstance(learning_context, Exception):
            learning_context = ""

        return memory_context, learning_context

    async def _get_learning_context(self, agent: BaseAgent, task: str) -> str:
        """Retrieve learned patterns relevant to the current task."""
        try:
            return await agent._recall_learned_patterns(task)
        except Exception:
            return ""

    # ------------------------------------------------------------------
    # Tool Execution with Safety
    # ------------------------------------------------------------------

    async def _execute_tools_with_safety(
        self,
        tool_calls: List[ToolCall],
        agent: BaseAgent,
        context: Dict[str, Any],
    ) -> List[ToolResult]:
        """Execute tool calls with permission checks, file locking, and hooks."""
        results: List[ToolResult] = []

        for tc in tool_calls:
            result = await self._execute_single_safe(tc, agent, context)
            results.append(result)

        return results

    async def _execute_single_safe(
        self,
        tc: ToolCall,
        agent: BaseAgent,
        context: Dict[str, Any],
    ) -> ToolResult:
        """
        Execute a single tool call with safety:
        - Permission check
        - File locking for write operations
        - Pre/post hooks
        """
        # Permission check
        try:
            from services.permission_service import check_permission

            allowed = await check_permission(
                tool_name=tc.tool_name,
                arguments=tc.arguments,
                agent_role=agent.role,
            )
            if not allowed:
                return ToolResult(
                    tool_call_id=tc.id,
                    success=False,
                    error=f"Permission denied for tool '{tc.tool_name}'",
                )
        except ImportError:
            # No permission service, allow by default
            pass
        except Exception as e:
            logger.warning(f"Permission check error: {e}, allowing by default")

        # File locking for write operations
        file_path = tc.arguments.get("path") or tc.arguments.get("file_path")
        lock_acquired = False

        if file_path and tc.tool_name in ("file_write", "file_append", "file_delete"):
            try:
                from services.file_lock import acquire_lock, release_lock

                lock_acquired = await acquire_lock(file_path, agent.id)
                if not lock_acquired:
                    return ToolResult(
                        tool_call_id=tc.id,
                        success=False,
                        error=f"File locked by another agent: {file_path}",
                    )
            except ImportError:
                pass

        # Pre-hook
        try:
            from services.tool_hooks import run_pre_hook

            await run_pre_hook(tc, agent)
        except ImportError:
            pass
        except Exception as e:
            logger.debug(f"Pre-hook error (non-fatal): {e}")

        # Execute
        result = await agent._execute_single_tool(tc)

        # Post-hook
        try:
            from services.tool_hooks import run_post_hook

            await run_post_hook(tc, result, agent)
        except ImportError:
            pass
        except Exception as e:
            logger.debug(f"Post-hook error (non-fatal): {e}")

        # Release file lock
        if lock_acquired and file_path:
            try:
                from services.file_lock import release_lock

                await release_lock(file_path, agent.id)
            except (ImportError, Exception):
                pass

        # Emit tool event
        asyncio.create_task(
            agent._emit_event("tool_call", {
                "tool": tc.tool_name,
                "success": result.success,
                "duration_ms": result.duration_ms,
            })
        )

        return result

    # ------------------------------------------------------------------
    # Context Compaction
    # ------------------------------------------------------------------

    def _needs_compaction(self, messages: List[Dict[str, Any]]) -> bool:
        """Check if messages exceed 80% of the context threshold."""
        try:
            from config import settings

            threshold = settings.context_summarize_threshold
            estimated = self._estimate_tokens(messages)
            return estimated > (threshold * 0.8)
        except Exception:
            return False

    async def _compact_context(
        self,
        messages: List[Dict[str, Any]],
        agent: BaseAgent,
    ) -> List[Dict[str, Any]]:
        """Compact conversation context by summarizing older messages."""
        try:
            from services.context_manager import get_context_manager

            cm = get_context_manager()
            return await cm.compact(messages, agent.model)
        except ImportError:
            # Simple compaction: keep system + first user + last 8 messages
            if len(messages) <= 10:
                return messages

            system_msgs = [m for m in messages[:2] if m.get("role") == "system"]
            recent = messages[-8:]

            # Create a summary of dropped messages
            dropped = messages[len(system_msgs):-8]
            summary_parts = []
            for m in dropped:
                role = m.get("role", "unknown")
                content = m.get("content", "")[:100]
                summary_parts.append(f"[{role}]: {content}...")

            summary_msg = {
                "role": "system",
                "content": (
                    "[Context Summary - older messages condensed]\n"
                    + "\n".join(summary_parts[-5:])
                ),
            }

            return system_msgs + [summary_msg] + recent

    # ------------------------------------------------------------------
    # Sub-Agent Dispatch
    # ------------------------------------------------------------------

    def _should_dispatch_subagent(
        self,
        response: str,
        results: List[ToolResult],
    ) -> bool:
        """Determine if the response warrants dispatching a sub-agent."""
        # Heuristic: if response mentions delegation or complexity
        delegation_signals = (
            "delegate to",
            "spawn agent",
            "need specialist",
            "sub-task:",
            "assign to",
        )
        response_lower = response.lower()
        return any(signal in response_lower for signal in delegation_signals)

    async def _dispatch_subagent(
        self,
        parent_agent: BaseAgent,
        response: str,
        results: List[ToolResult],
        context: Dict[str, Any],
    ) -> Optional[str]:
        """Dispatch a sub-agent for a delegated task."""
        try:
            from agents.factory import AgentFactory

            factory = AgentFactory()

            # Determine role and task from response context
            # Simple heuristic: look for role mentions
            role_map = {
                "code": AgentRole.CODER,
                "research": AgentRole.RESEARCHER,
                "write": AgentRole.WRITER,
                "execute": AgentRole.EXECUTOR,
                "review": AgentRole.REVIEWER,
                "plan": AgentRole.PLANNER,
            }

            target_role = AgentRole.CODER  # Default
            response_lower = response.lower()
            for keyword, role in role_map.items():
                if keyword in response_lower:
                    target_role = role
                    break

            # Extract sub-task (last sentence or explicit sub-task marker)
            sub_task = response.split("\n")[-1].strip() or response[:200]

            result = await factory.execute_task(
                role=target_role,
                task=sub_task,
                context=context,
            )
            return result
        except Exception as e:
            logger.warning(f"Sub-agent dispatch failed: {e}")
            return None

    # ------------------------------------------------------------------
    # Post-Hooks & Observations
    # ------------------------------------------------------------------

    def _get_post_hook_content(self, results: List[ToolResult], agent: BaseAgent) -> str:
        """Generate system reminders after tool execution."""
        reminders: List[str] = []

        # Check for errors that need attention
        errors = [r for r in results if not r.success]
        if errors:
            reminders.append(
                f"[System] {len(errors)} tool call(s) failed. "
                "Consider retrying with different parameters or reporting the issue."
            )

        # Check for destructive operations completed
        if agent._actions_taken > 5:
            reminders.append(
                "[System] Multiple actions taken. Consider summarizing progress."
            )

        return "\n".join(reminders)

    def _format_observations(self, results: List[ToolResult]) -> str:
        """Format tool results as observations for the agent."""
        if not results:
            return "[No tool results]"

        parts: List[str] = []
        for i, r in enumerate(results, 1):
            if r.success:
                output = r.output or "Done (no output)"
                # Truncate very long outputs
                if len(output) > 2000:
                    output = output[:2000] + "\n... [truncated]"
                parts.append(f"[Observation {i}] ✓ {output}")
            else:
                parts.append(f"[Observation {i}] ✗ Error: {r.error}")

        return "\n\n".join(parts)

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    def _estimate_tokens(self, messages: List[Dict[str, Any]]) -> int:
        """Estimate token count from messages (chars // 4 approximation)."""
        total_chars = sum(len(m.get("content", "")) for m in messages)
        return total_chars // 4

    def _record_outcome(
        self,
        agent: BaseAgent,
        task: str,
        result: str,
        duration_ms: float,
        success: bool,
    ) -> None:
        """Record task outcome for agent learning (non-blocking)."""
        try:
            from services.agent_learning import record_outcome

            asyncio.create_task(
                record_outcome(
                    agent_role=agent.role,
                    task=task,
                    result=result[:500],
                    duration_ms=duration_ms,
                    success=success,
                    tokens_used=agent._total_tokens_used,
                )
            )
        except ImportError:
            pass
        except Exception as e:
            logger.debug(f"Outcome recording skipped: {e}")
