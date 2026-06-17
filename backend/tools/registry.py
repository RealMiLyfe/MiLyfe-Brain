"""MiLyfe Brain — Central Tool Registry."""

from __future__ import annotations

import time
import uuid
from typing import Any, Callable, Dict, List, Optional

import structlog

from models.schemas import PermissionLevel, ToolCall, ToolDefinition, ToolResult

logger = structlog.get_logger()


class ToolRegistry:
    """Central registry for all agent tools."""

    def __init__(self):
        self._tools: Dict[str, Dict[str, Any]] = {}

    def register(
        self,
        name: str,
        handler: Callable,
        category: str,
        description: str,
        parameters: Dict[str, Any] = None,
        permission: PermissionLevel = PermissionLevel.FREE,
        returns: str = "string",
    ):
        """Register a tool."""
        self._tools[name] = {
            "name": name,
            "handler": handler,
            "category": category,
            "description": description,
            "parameters": parameters or {},
            "permission": permission,
            "returns": returns,
        }

    async def execute(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        agent: Any = None,
    ) -> ToolResult:
        """Execute a tool by name."""
        if tool_name not in self._tools:
            return ToolResult(
                tool_name=tool_name,
                success=False,
                error=f"Unknown tool: {tool_name}",
            )

        tool = self._tools[tool_name]

        # Check permissions
        from safety.permissions import check_permission
        allowed, reason = await check_permission(
            tool_name=tool_name,
            permission=tool["permission"],
            agent=agent,
            arguments=arguments,
        )
        if not allowed:
            return ToolResult(
                tool_name=tool_name,
                success=False,
                error=f"Permission denied: {reason}",
            )

        # Execute
        start = time.time()
        try:
            handler = tool["handler"]
            import asyncio
            if asyncio.iscoroutinefunction(handler):
                output = await handler(**arguments)
            else:
                output = handler(**arguments)

            elapsed = (time.time() - start) * 1000

            # Log execution
            await self._log_execution(tool_name, arguments, output, agent)

            return ToolResult(
                tool_name=tool_name,
                success=True,
                output=str(output) if output is not None else "",
                execution_time_ms=elapsed,
                call_id=str(uuid.uuid4())[:8],
            )

        except Exception as e:
            elapsed = (time.time() - start) * 1000
            logger.error("tool_execution_error", tool=tool_name, error=str(e))
            return ToolResult(
                tool_name=tool_name,
                success=False,
                error=str(e),
                execution_time_ms=elapsed,
            )

    def get_tool(self, name: str) -> Optional[ToolDefinition]:
        """Get tool definition."""
        tool = self._tools.get(name)
        if not tool:
            return None
        return ToolDefinition(
            name=tool["name"],
            category=tool["category"],
            description=tool["description"],
            parameters=tool["parameters"],
            permission=tool["permission"],
            returns=tool["returns"],
        )

    def list_tools(self) -> List[ToolDefinition]:
        """List all registered tools."""
        return [
            ToolDefinition(
                name=t["name"],
                category=t["category"],
                description=t["description"],
                parameters=t["parameters"],
                permission=t["permission"],
                returns=t["returns"],
            )
            for t in self._tools.values()
        ]

    def list_tools_for_prompt(self) -> str:
        """Format tools for inclusion in agent prompts."""
        lines = ["Available tools:"]
        for t in self._tools.values():
            params = ", ".join(f"{k}: {v}" for k, v in t["parameters"].items())
            lines.append(f"- {t['name']}({params}): {t['description']}")
        return "\n".join(lines)

    async def _log_execution(self, tool_name: str, args: dict, output: Any, agent: Any):
        """Log tool execution to audit trail."""
        try:
            from safety.logger import audit_logger
            await audit_logger.log_tool_execution(
                tool_name=tool_name,
                arguments=args,
                output=str(output)[:500] if output else "",
                agent=agent,
            )
        except Exception:
            pass


# Singleton
tool_registry = ToolRegistry()


def _register_all_tools():
    """Register all built-in tools at import time."""
    from tools.file_tools import register_file_tools
    from tools.shell_tools import register_shell_tools
    from tools.code_tools import register_code_tools
    from tools.browser_tools import register_browser_tools
    from tools.gui_tools import register_gui_tools
    from tools.search_tools import register_search_tools
    from tools.batch_tools import register_batch_tools
    from tools.repl_tools import register_repl_tools
    from tools.scratchpad_tools import register_scratchpad_tools

    register_file_tools(tool_registry)
    register_shell_tools(tool_registry)
    register_code_tools(tool_registry)
    register_browser_tools(tool_registry)
    register_gui_tools(tool_registry)
    register_search_tools(tool_registry)
    register_batch_tools(tool_registry)
    register_repl_tools(tool_registry)
    register_scratchpad_tools(tool_registry)


_register_all_tools()
