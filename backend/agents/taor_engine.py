"""MiLyfe Brain — TAOR Engine (Think-Act-Observe-Repeat).

Reverse-engineered from Claude Code architecture:
- Topic detection (light model call to classify input type)
- Layered prompt augmentation (system → CLAUDE.md → skills → hooks → sub-agents)
- Context compaction (summarize when nearing token limit)
- Sub-agent dispatch (isolated context for heavy subtasks)
- Permission pre-checks before tool execution
- Deterministic hooks (pre/post tool interception)

This replaces the simple think() loop with a full TAOR harness.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from datetime import datetime
from typing import Any, AsyncGenerator, Callable, Dict, List, Optional, Tuple

import structlog

from config import settings
from models.schemas import (
    AgentRole,
    AgentState,
    EventType,
    OutputStyle,
    ToolCall,
    ToolResult,
    TopicType,
)

logger = structlog.get_logger()


# ─── Prompt Injection Points (Layers) ──────────────────────────
# Each layer injects at a specific point in the API payload:
#
# 1. SYSTEM PROMPT — Base identity + output style
# 2. RULES (CLAUDE.md equivalent) — Project rules, conventions
# 3. ENVIRONMENT — Dir tree, git status, runtime info
# 4. MEMORY — Relevant vector recall + learned corrections
# 5. SKILLS — Auto-activated domain expertise
# 6. SCRATCHPAD — Short-term working memory (survives compaction)
# 7. TOOLS — Available tool definitions
# 8. USER MESSAGE — The actual task/input
# 9. POST-HOOKS — Injected after tool results (system-reminder style)


class PromptLayer:
    """A single prompt augmentation layer."""

    def __init__(self, name: str, priority: int, content_fn: Callable, active: bool = True):
        self.name = name
        self.priority = priority  # Lower = injected first
        self.content_fn = content_fn  # async fn(context) -> str
        self.active = active


class TAOREngine:
    """Think-Act-Observe-Repeat execution engine.

    This is the core harness that drives agent behavior, modeled after
    the Claude Code architecture with:
    - Topic detection before execution
    - Layered prompt construction
    - Tool execution with permission checks and hooks
    - Context compaction when approaching limits
    - Sub-agent dispatch for isolated subtasks
    """

    def __init__(self):
        self._layers: List[PromptLayer] = []
        self._max_turns: int = 10  # Max TAOR iterations per task
        self._compaction_threshold: int = settings.context_summarize_threshold
        self._register_default_layers()

    # ─── Public Interface ───────────────────────────────────────

    async def execute(
        self,
        agent,  # BaseAgent instance
        task: str,
        context: Optional[Dict[str, Any]] = None,
        max_turns: Optional[int] = None,
        output_style: OutputStyle = OutputStyle.DEFAULT,
        stream: bool = False,
    ) -> str:
        """Execute the full TAOR loop for a task.

        1. Detect topic type (new_task, follow_up, question, etc.)
        2. Build layered system prompt
        3. LOOP: Think → Act → Observe → Repeat
        4. Compact context if needed
        5. Return final response
        """
        context = context or {}
        max_turns = max_turns or self._max_turns
        start_time = time.time()

        # ── Step 1: Topic Detection ─────────────────────────────
        topic_type = await self._detect_topic(task, context)
        context["topic_type"] = topic_type.value

        # Determine if context should reset
        if topic_type == TopicType.NEW_TASK and not context.get("continuation"):
            agent._messages = []  # Fresh context for new tasks

        # ── Step 2: Build Layered Prompt ────────────────────────
        system_prompt = await self._build_layered_prompt(agent, task, context, output_style)

        # Initialize messages if fresh
        if not agent._messages:
            agent._messages = [{"role": "system", "content": system_prompt}]

        # Add user message
        agent._messages.append({"role": "user", "content": task})

        # Emit start event
        agent._emit_event(EventType.AGENT_SPAWNED, {
            "task": task[:200],
            "topic": topic_type.value,
            "model": agent.model,
            "context_tokens": self._estimate_tokens(agent._messages),
        })

        # ── Step 3: TAOR Loop ───────────────────────────────────
        final_response = ""

        for turn in range(max_turns):
            # Check if compaction needed BEFORE calling LLM
            if self._needs_compaction(agent._messages):
                agent._messages = await self._compact_context(agent._messages, agent)
                logger.debug("context_compacted", agent_id=agent.id, turn=turn)

            # ── THINK: Call LLM ─────────────────────────────────
            response_text = await agent._call_llm_safe(stream=stream)

            if not response_text:
                final_response = "[No response from model. It may be unavailable.]"
                break

            # Record thought
            agent._thoughts.append(response_text[:300])
            agent._emit_event(EventType.THOUGHT, {
                "content": response_text[:500],
                "turn": turn,
                "tokens_used": agent._total_tokens_used,
            })

            # ── ACT: Parse for tool calls ───────────────────────
            from agents.tool_parser import parse_tool_calls
            tool_calls = parse_tool_calls(response_text)

            if not tool_calls:
                # No tool calls = final response
                final_response = response_text
                break

            # ── OBSERVE: Execute tools + inject results ─────────
            tool_results = await self._execute_tools_with_safety(
                tool_calls, agent, context
            )

            # Format and inject results
            observation = self._format_observations(tool_results)

            # Add assistant message + tool results to context
            agent._messages.append({"role": "assistant", "content": response_text})

            # Inject post-tool hooks (system-reminder style)
            post_hook_content = await self._get_post_hook_content(tool_results, agent)
            if post_hook_content:
                observation += f"\n\n{post_hook_content}"

            agent._messages.append({"role": "user", "content": observation})

            # Update progress
            agent._progress = (turn + 1) / max_turns

            # ── REPEAT: Check if we should dispatch sub-agent ───
            if self._should_dispatch_subagent(response_text, tool_results):
                sub_result = await self._dispatch_subagent(
                    agent, response_text, tool_results, context
                )
                if sub_result:
                    agent._messages.append({
                        "role": "user",
                        "content": f"[Sub-agent result]:\n{sub_result[:2000]}",
                    })

        # ── Step 4: Post-completion ─────────────────────────────
        duration = time.time() - start_time
        agent._progress = 1.0

        # Fire-and-forget post-completion tasks
        asyncio.create_task(agent._post_completion(task, final_response, duration))

        agent._emit_event(EventType.COMPLETED, {
            "response_length": len(final_response),
            "turns": min(turn + 1, max_turns),
            "duration_s": round(duration, 2),
            "total_tokens": agent._total_tokens_used,
            "topic": topic_type.value,
        })

        # Record success/failure for learning
        try:
            from services.agent_learning import agent_learning
            if final_response and "error" not in final_response.lower()[:50]:
                agent_learning.record_success(agent.role, task)
            elif not final_response:
                agent_learning.record_failure(agent.role, "Empty response", task)
        except Exception:
            pass

        return final_response

    # ─── Topic Detection ────────────────────────────────────────

    async def _detect_topic(self, text: str, context: Dict) -> TopicType:
        """Classify input topic type (fast heuristic, no LLM call needed).

        Claude Code uses a light Haiku call for this. We use fast regex/keyword
        heuristics that handle 80%+ of cases without any LLM cost.
        """
        from services.topic_detector import detect_topic

        history_length = context.get("history_length", 0)
        topic, confidence = detect_topic(text, history_length)

        logger.debug("topic_detected", topic=topic.value, confidence=confidence)
        return topic

    # ─── Layered Prompt Construction ────────────────────────────

    async def _build_layered_prompt(
        self,
        agent,
        task: str,
        context: Dict,
        output_style: OutputStyle,
    ) -> str:
        """Build the full system prompt from all augmentation layers.

        Layers (in injection order):
        1. Base system prompt (role identity)
        2. Output style instructions
        3. Project rules (.milyfe/rules/ hierarchy)
        4. Environment snapshot (dir tree, git, runtime)
        5. Memory (vector recall + learned corrections + failure prevention)
        6. Skills (auto-activated by input keywords)
        7. Scratchpad (short-term working memory)
        8. Tools (available tool definitions)
        9. Project intelligence (type, key files, dependencies)
        """
        parts = []

        # Layer 1: Base identity
        parts.append(agent.system_prompt())
        parts.append(f"\nYou are '{agent.name}' (role: {agent.role.value}), part of MiLyfe Brain agent swarm.")

        # Layer 2: Output style
        from prompts.output_styles import get_style_instruction
        style_inst = get_style_instruction(output_style)
        if style_inst:
            parts.append(f"\n[Output Style: {output_style.value}]\n{style_inst}")

        # Layer 3: Project rules (CLAUDE.md equivalent)
        try:
            from prompts.rule_loader import rule_loader
            rules = rule_loader.get_rules_for_prompt(role=agent.role.value)
            if rules:
                parts.append(f"\n{rules}")
        except Exception:
            pass

        # Layer 4: Environment snapshot
        try:
            from services.env_snapshot import env_snapshot
            env_ctx = env_snapshot.get_for_prompt()
            if env_ctx:
                parts.append(env_ctx)
        except Exception:
            pass

        # Layer 5: Memory (parallel fetch for speed)
        memory_parts = await self._fetch_memory_layers(agent, task)
        if memory_parts:
            parts.append(memory_parts)

        # Layer 6: Semantic skills
        try:
            from services.semantic_skills import semantic_skills
            active_skills = semantic_skills.get_active_skills(task)
            if active_skills:
                instructions = semantic_skills.get_skill_instructions(active_skills)
                if instructions:
                    parts.append(f"\n[Active Skills: {', '.join(active_skills)}]\n{instructions}")
        except Exception:
            pass

        # Layer 7: Scratchpad
        try:
            from tools.scratchpad_tools import get_scratchpad_context
            session_id = context.get("session_id", "default")
            scratch = get_scratchpad_context(session_id)
            if scratch:
                parts.append(scratch)
        except Exception:
            pass

        # Layer 8: Tools
        try:
            from tools.registry import tool_registry
            tools_prompt = tool_registry.list_tools_for_prompt()
            parts.append(f"\n{tools_prompt}")
            parts.append('\nTo use a tool, output JSON: {"tool": "name", "args": {...}}')
            parts.append("You can make multiple tool calls per response.")
            parts.append("After receiving tool results, continue reasoning toward the answer.")
        except Exception:
            pass

        # Layer 9: Project intelligence
        try:
            from services.project_intelligence import project_intelligence
            proj_ctx = project_intelligence.get_context_for_agent(task)
            if proj_ctx:
                parts.append(proj_ctx)
        except Exception:
            pass

        return "\n\n".join(parts)

    async def _fetch_memory_layers(self, agent, task: str) -> str:
        """Fetch all memory layers in parallel for speed."""
        parts = []

        try:
            results = await asyncio.gather(
                agent._recall_context(task),
                agent._recall_learned_patterns(task),
                self._get_learning_context(agent, task),
                return_exceptions=True,
            )

            for r in results:
                if isinstance(r, str) and r:
                    parts.append(r)
        except Exception:
            pass

        return "\n".join(parts) if parts else ""

    async def _get_learning_context(self, agent, task: str) -> str:
        """Get agent learning context (corrections, failure prevention, specialization)."""
        try:
            from services.agent_learning import agent_learning
            return agent_learning.get_learning_context(agent.role, task)
        except Exception:
            return ""

    # ─── Tool Execution with Safety ─────────────────────────────

    async def _execute_tools_with_safety(
        self,
        tool_calls: List[ToolCall],
        agent,
        context: Dict,
    ) -> List[ToolResult]:
        """Execute tools with full safety pipeline:

        1. Permission check (free/notify/approve/blocked)
        2. Pre-hooks (sanitize paths, validate params, audit)
        3. Execute tool
        4. Post-hooks (truncate output, format, log)
        5. Record in project intelligence (file lock tracking)
        """
        results = []

        # Determine if tools can run in parallel
        if len(tool_calls) > 1 and agent._can_parallelize(tool_calls):
            # Parallel execution
            tasks = [self._execute_single_safe(tc, agent, context) for tc in tool_calls]
            results = await asyncio.gather(*tasks)
        else:
            # Sequential execution
            for tc in tool_calls:
                result = await self._execute_single_safe(tc, agent, context)
                results.append(result)

        return results

    async def _execute_single_safe(
        self, tc: ToolCall, agent, context: Dict
    ) -> ToolResult:
        """Execute a single tool with full safety checks."""
        agent._actions_taken += 1

        # Emit tool_call event (UI shows what's about to happen)
        agent._emit_event(EventType.TOOL_CALL, {
            "tool": tc.tool_name,
            "args": {k: str(v)[:100] for k, v in tc.arguments.items()},
            "preview": True,  # Signals UI to show preview before execution
        })

        try:
            # 1. Pre-hooks (can modify params or block)
            from hooks.registry import hook_registry
            tc = await hook_registry.run_pre_hooks(tc, agent)

            # 2. Permission check
            from safety.permissions import check_permission
            from tools.registry import tool_registry
            tool_def = tool_registry.get_tool(tc.tool_name)
            if tool_def:
                allowed, reason = await check_permission(
                    tool_name=tc.tool_name,
                    permission=tool_def.permission,
                    agent=agent,
                    arguments=tc.arguments,
                )
                if not allowed:
                    return ToolResult(
                        tool_name=tc.tool_name,
                        success=False,
                        error=f"Permission denied: {reason}",
                    )

            # 3. Track file access in project intelligence
            if tc.tool_name in ("file_read", "file_write", "file_delete"):
                try:
                    from services.project_intelligence import project_intelligence
                    path = tc.arguments.get("path", "")
                    if tc.tool_name == "file_write":
                        if not project_intelligence.acquire_file_lock(path, agent.id):
                            return ToolResult(
                                tool_name=tc.tool_name,
                                success=False,
                                error=f"File conflict: {path} is being edited by another agent",
                            )
                    project_intelligence.record_file_access(path, agent.id)
                except Exception:
                    pass

            # 4. Execute
            result = await tool_registry.execute(tc.tool_name, tc.arguments, agent=agent)

            # 5. Post-hooks (can transform output)
            result = await hook_registry.run_post_hooks(result, agent)

            # 6. Release file lock if write
            if tc.tool_name == "file_write":
                try:
                    from services.project_intelligence import project_intelligence
                    project_intelligence.release_file_lock(
                        tc.arguments.get("path", ""), agent.id
                    )
                except Exception:
                    pass

            # Emit result
            agent._emit_event(EventType.TOOL_RESULT, {
                "tool": tc.tool_name,
                "success": result.success,
                "output_preview": result.output[:200] if result.output else "",
                "execution_time_ms": result.execution_time_ms,
            })

            return result

        except Exception as e:
            logger.error("taor_tool_error", tool=tc.tool_name, error=str(e))
            return ToolResult(tool_name=tc.tool_name, success=False, error=str(e))

    # ─── Context Compaction ─────────────────────────────────────

    def _needs_compaction(self, messages: List[Dict]) -> bool:
        """Check if messages are approaching the token limit."""
        estimated = self._estimate_tokens(messages)
        return estimated > self._compaction_threshold * 0.8  # Compact at 80%

    async def _compact_context(self, messages: List[Dict], agent) -> List[Dict]:
        """Compact context by summarizing older messages.

        Preserves:
        - System prompt (always)
        - Scratchpad content (re-injected)
        - Last 4 messages (recent context)
        - Key decisions and file modifications

        Summarizes everything else into a compact block.
        """
        try:
            from services.context_manager import context_manager
            compacted = await context_manager.compact(messages)
            agent._emit_event(EventType.PROGRESS, {
                "compaction": True,
                "before_msgs": len(messages),
                "after_msgs": len(compacted),
                "saved_tokens": self._estimate_tokens(messages) - self._estimate_tokens(compacted),
            })
            return compacted
        except Exception as e:
            logger.warning("compaction_failed", error=str(e))
            # Fallback: keep system + last 6 messages
            system = [m for m in messages if m["role"] == "system"]
            recent = [m for m in messages if m["role"] != "system"][-6:]
            return system + recent

    # ─── Sub-Agent Dispatch ─────────────────────────────────────

    def _should_dispatch_subagent(self, response: str, results: List[ToolResult]) -> bool:
        """Determine if a sub-agent should be dispatched.

        Triggers:
        - Response mentions needing deep research
        - Tool results are very long (need summarization)
        - Response explicitly requests delegation
        """
        # Check for explicit delegation signals
        delegation_signals = [
            "need to research", "let me investigate",
            "this requires deeper analysis", "delegate to",
            "sub-task:", "dispatch:",
        ]
        response_lower = response.lower()
        if any(signal in response_lower for signal in delegation_signals):
            return True

        # Check for very long tool results (need summarization)
        total_output = sum(len(r.output or "") for r in results)
        if total_output > 8000:
            return True

        return False

    async def _dispatch_subagent(
        self, parent_agent, response: str, results: List[ToolResult], context: Dict
    ) -> Optional[str]:
        """Dispatch an isolated sub-agent for a subtask.

        The sub-agent:
        - Gets its own context (no pollution)
        - Only returns the FINAL result to parent
        - All intermediate reasoning is discarded
        """
        try:
            from services.subagent_isolation import subagent_isolation

            # Determine the sub-task
            # Look for explicit delegation in response
            import re
            delegation_match = re.search(
                r"(?:delegate|dispatch|sub-task):\s*(.+?)(?:\n|$)",
                response,
                re.IGNORECASE,
            )

            if delegation_match:
                sub_task = delegation_match.group(1).strip()
            else:
                # Summarize long tool results
                long_results = [r for r in results if len(r.output or "") > 3000]
                if long_results:
                    sub_task = f"Summarize these results concisely:\n" + "\n---\n".join(
                        r.output[:2000] for r in long_results
                    )
                else:
                    return None

            # Choose appropriate role for sub-agent
            role = self._infer_subagent_role(sub_task)

            result = await subagent_isolation.run_isolated(
                role=role,
                task=sub_task,
                context={"parent_agent": parent_agent.id, **context},
            )

            logger.info("subagent_completed",
                       parent=parent_agent.id,
                       sub_role=role.value,
                       result_len=len(result))

            return result

        except Exception as e:
            logger.warning("subagent_dispatch_failed", error=str(e))
            return None

    def _infer_subagent_role(self, task: str) -> AgentRole:
        """Infer the best role for a sub-agent based on the task."""
        task_lower = task.lower()
        if any(w in task_lower for w in ["research", "search", "find", "look up"]):
            return AgentRole.RESEARCHER
        if any(w in task_lower for w in ["summarize", "write", "document"]):
            return AgentRole.WRITER
        if any(w in task_lower for w in ["review", "check", "verify"]):
            return AgentRole.CRITIC
        if any(w in task_lower for w in ["debug", "fix", "error"]):
            return AgentRole.DEBUGGER
        return AgentRole.CODER

    # ─── Post-Hook Content ──────────────────────────────────────

    async def _get_post_hook_content(self, results: List[ToolResult], agent) -> str:
        """Generate post-tool-execution system reminders.

        Injected after tool results (like Claude Code's <system-reminder> tags).
        Used for:
        - Safety warnings for dangerous results
        - Reminders about project conventions
        - Context about related files
        """
        reminders = []

        for r in results:
            if not r.success:
                # Failed tool: remind about error handling
                reminders.append(
                    f"[Reminder: {r.tool_name} failed. Analyze the error and try a different approach.]"
                )

            if r.tool_name == "file_write" and r.success:
                # After file write: remind about testing
                reminders.append(
                    "[Reminder: After modifying code, consider if tests need updating.]"
                )

            if r.tool_name == "shell_exec" and r.success and "error" in (r.output or "").lower():
                reminders.append(
                    "[Reminder: Shell output contains 'error'. Check if the command actually succeeded.]"
                )

        return "\n".join(reminders) if reminders else ""

    # ─── Observations Formatting ────────────────────────────────

    def _format_observations(self, results: List[ToolResult]) -> str:
        """Format tool results as observations for the next Think step."""
        parts = ["Tool execution results:"]
        for r in results:
            if r.success:
                output = r.output[:3000] if r.output else "(no output)"
                parts.append(f"\n[{r.tool_name}] SUCCESS ({r.execution_time_ms:.0f}ms):\n{output}")
            else:
                parts.append(f"\n[{r.tool_name}] FAILED: {r.error}")
        return "\n".join(parts)

    # ─── Helpers ────────────────────────────────────────────────

    def _estimate_tokens(self, messages: List[Dict]) -> int:
        """Estimate token count (4 chars ≈ 1 token)."""
        return sum(len(m.get("content", "")) for m in messages) // 4

    def _register_default_layers(self):
        """Register default prompt augmentation layers."""
        # Layers are registered for documentation/extensibility
        # Actual injection happens in _build_layered_prompt
        self._layers = [
            PromptLayer("system", 0, lambda ctx: ""),
            PromptLayer("output_style", 1, lambda ctx: ""),
            PromptLayer("rules", 2, lambda ctx: ""),
            PromptLayer("environment", 3, lambda ctx: ""),
            PromptLayer("memory", 4, lambda ctx: ""),
            PromptLayer("skills", 5, lambda ctx: ""),
            PromptLayer("scratchpad", 6, lambda ctx: ""),
            PromptLayer("tools", 7, lambda ctx: ""),
            PromptLayer("project", 8, lambda ctx: ""),
        ]


# Singleton
taor_engine = TAOREngine()
