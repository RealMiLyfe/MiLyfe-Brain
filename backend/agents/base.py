"""BaseAgent — Abstract base class for all AI agents.

Implements the think/act loop with tool execution, memory recall,
and inter-agent communication via httpx → Ollama.
"""

import asyncio
import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Optional

import httpx
import structlog

from config import settings

logger = structlog.get_logger()


class BaseAgent(ABC):
    """Abstract base agent with think/act execution loop."""

    def __init__(
        self,
        role: str,
        name: str,
        model: Optional[str] = None,
        tools: Optional[list[str]] = None,
        max_rounds: int = 3,
    ):
        self.id = str(uuid.uuid4())
        self.role = role
        self.name = name
        self.model = model or settings.default_heavy_model
        self.tools = tools or []
        self.max_rounds = max_rounds
        self.status = "idle"
        self.current_task: Optional[str] = None
        self.thoughts: list[str] = []
        self.actions_taken: list[dict] = []
        self.progress: float = 0.0
        self.created_at = datetime.utcnow()
        self.avatar_color = self._get_avatar_color()

    @abstractmethod
    def get_system_prompt(self) -> str:
        """Return the system prompt for this agent role."""
        ...

    def _get_avatar_color(self) -> str:
        """Return a color for the agent avatar based on role."""
        colors = {
            "orchestrator": "#6366f1",
            "researcher": "#06b6d4",
            "coder": "#10b981",
            "executor": "#f59e0b",
            "critic": "#ef4444",
            "designer": "#8b5cf6",
            "writer": "#ec4899",
            "debugger": "#f97316",
            "planner": "#14b8a6",
        }
        return colors.get(self.role, "#6b7280")

    async def think(
        self,
        task: str,
        context: Optional[str] = None,
        memory_results: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        """Execute the think/act loop.

        1. Build system prompt with role + rules + context
        2. Recall relevant memories (if available)
        3. Call Ollama /api/chat via httpx
        4. Parse for tool calls
        5. Execute tools (with hooks)
        6. Feed results back (max N rounds)
        7. Return final response
        """
        self.status = "thinking"
        self.current_task = task
        self.thoughts = []
        self.actions_taken = []
        self.progress = 0.0

        # Build messages
        messages = [{"role": "system", "content": self._build_system_prompt(context, memory_results)}]
        messages.append({"role": "user", "content": task})

        result = {"response": "", "tool_calls": [], "error": None}

        try:
            for round_num in range(self.max_rounds + 1):
                self.progress = round_num / (self.max_rounds + 1)

                # Call Ollama
                response_text = await self._call_ollama(messages)
                self.thoughts.append(response_text[:200])

                # Parse for tool calls
                from agents.tool_parser import ToolParser

                tool_calls = ToolParser.parse(response_text)

                if not tool_calls or round_num == self.max_rounds:
                    # No tool calls or max rounds reached — this is the final response
                    result["response"] = response_text
                    break

                # Execute tool calls
                self.status = "acting"
                tool_results = await self._execute_tools(tool_calls)
                result["tool_calls"].extend(tool_calls)

                # Add assistant message and tool results to conversation
                messages.append({"role": "assistant", "content": response_text})
                tool_result_text = "\n".join(
                    [f"Tool `{tc['name']}` result:\n{tr}" for tc, tr in zip(tool_calls, tool_results)]
                )
                messages.append({"role": "user", "content": f"Tool results:\n{tool_result_text}"})

                self.status = "thinking"

        except Exception as e:
            logger.error("Agent think loop failed", agent=self.name, error=str(e))
            result["error"] = str(e)

        self.status = "idle"
        self.current_task = None
        self.progress = 1.0

        return result

    def _build_system_prompt(
        self,
        context: Optional[str] = None,
        memory_results: Optional[list[str]] = None,
    ) -> str:
        """Build the complete system prompt with role, context, and memories."""
        parts = [self.get_system_prompt()]

        if memory_results:
            parts.append("\n## Relevant Memories\n" + "\n".join(f"- {m}" for m in memory_results))

        if context:
            parts.append(f"\n## Additional Context\n{context}")

        # Tool instructions
        if self.tools:
            parts.append(self._get_tool_instructions())

        return "\n\n".join(parts)

    def _get_tool_instructions(self) -> str:
        """Generate tool usage instructions for the system prompt."""
        from tools.registry import tool_registry

        instructions = ["## Available Tools", "Call tools using JSON format:"]
        instructions.append('```json\n{"tool": "tool_name", "params": {"param1": "value1"}}\n```\n')

        for tool_name in self.tools:
            tool_info = tool_registry.get_tool_info(tool_name)
            if tool_info:
                instructions.append(f"- **{tool_name}**: {tool_info.get('description', 'No description')}")

        return "\n".join(instructions)

    async def _call_ollama(self, messages: list[dict]) -> str:
        """Call Ollama /api/chat via httpx."""
        async with httpx.AsyncClient(timeout=settings.agent_timeout) as client:
            response = await client.post(
                f"{settings.ollama_base_url}/api/chat",
                json={
                    "model": self.model,
                    "messages": messages,
                    "stream": False,
                    "options": {"temperature": 0.7, "num_predict": 4096},
                },
            )
            response.raise_for_status()
            data = response.json()
            return data.get("message", {}).get("content", "")

    async def _execute_tools(self, tool_calls: list[dict]) -> list[str]:
        """Execute parsed tool calls through the tool registry."""
        from tools.registry import tool_registry

        results = []
        for call in tool_calls:
            tool_name = call.get("name", call.get("tool", ""))
            params = call.get("params", call.get("arguments", {}))

            self.actions_taken.append(
                {"tool": tool_name, "params": params, "timestamp": datetime.utcnow().isoformat()}
            )

            try:
                result = await tool_registry.execute(tool_name, params, agent_id=self.id, agent_role=self.role)
                results.append(str(result))
            except Exception as e:
                logger.error("Tool execution failed", tool=tool_name, error=str(e))
                results.append(f"Error: {str(e)}")

        return results

    def to_dict(self) -> dict[str, Any]:
        """Serialize agent state."""
        return {
            "id": self.id,
            "role": self.role,
            "name": self.name,
            "status": self.status,
            "current_task": self.current_task,
            "thoughts": self.thoughts,
            "actions_taken": self.actions_taken,
            "progress": self.progress,
            "model": self.model,
            "avatar_color": self.avatar_color,
            "created_at": self.created_at.isoformat(),
        }
