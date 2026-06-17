"""
MiLyfe Brain - Tool Registry

Central registry for all agent tools with permission management and execution.
"""
from __future__ import annotations

import asyncio
import inspect
import logging
import time
from typing import Any, Callable, Dict, List, Optional

from models.schemas import PermissionLevel, ToolCall, ToolDefinition, ToolResult

logger = logging.getLogger(__name__)


class ToolRegistry:
    """Singleton registry for all agent tools.

    Manages tool registration, discovery, permission checks, and execution.
    """

    _instance: Optional[ToolRegistry] = None
    _tools: Dict[str, Dict[str, Any]]
    _initialized: bool

    def __new__(cls) -> ToolRegistry:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._tools = {}
            cls._instance._initialized = False
        return cls._instance

    def register(
        self,
        name: str,
        handler: Callable[..., Any],
        category: str,
        description: str,
        parameters: Dict[str, Any],
        permission: PermissionLevel,
        returns: str,
    ) -> None:
        """Register a tool with the registry.

        Args:
            name: Unique tool name.
            handler: Callable that implements the tool.
            category: Tool category (filesystem, shell, code, etc.).
            description: Human-readable description.
            parameters: Parameter schema dict.
            permission: Required permission level.
            returns: Description of return value.
        """
        if name in self._tools:
            logger.warning("Tool '%s' is being re-registered", name)

        self._tools[name] = {
            "name": name,
            "handler": handler,
            "category": category,
            "description": description,
            "parameters": parameters,
            "permission": permission,
            "returns": returns,
        }
        logger.debug("Registered tool: %s [%s] (%s)", name, category, permission.value)

    async def execute(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        agent: Optional[str] = None,
    ) -> ToolResult:
        """Execute a tool with permission checking, timing, and audit logging.

        Args:
            tool_name: Name of the tool to execute.
            arguments: Arguments to pass to the tool handler.
            agent: Agent identifier for audit logging.

        Returns:
            ToolResult with success status, output/error, and duration.
        """
        start_time = time.perf_counter()
        call_id = f"{tool_name}_{int(time.time() * 1000)}"

        # Check tool exists
        if tool_name not in self._tools:
            return ToolResult(
                tool_call_id=call_id,
                success=False,
                error=f"Unknown tool: '{tool_name}'",
                duration_ms=0.0,
            )

        tool = self._tools[tool_name]
        permission = tool["permission"]
        handler = tool["handler"]

        # Permission check - log high-risk operations
        if permission in (PermissionLevel.DESTRUCTIVE, PermissionLevel.CRITICAL):
            logger.warning(
                "High-risk tool call: %s (permission=%s, agent=%s, args=%s)",
                tool_name,
                permission.value,
                agent,
                {k: str(v)[:100] for k, v in arguments.items()},
            )

        # Execute the handler
        try:
            if inspect.iscoroutinefunction(handler):
                result = await handler(**arguments)
            else:
                result = handler(**arguments)

            duration = (time.perf_counter() - start_time) * 1000

            logger.info(
                "Tool executed: %s (agent=%s, duration=%.1fms, success=True)",
                tool_name,
                agent,
                duration,
            )

            return ToolResult(
                tool_call_id=call_id,
                success=True,
                output=str(result) if result is not None else "(no output)",
                duration_ms=round(duration, 2),
            )

        except PermissionError as e:
            duration = (time.perf_counter() - start_time) * 1000
            logger.error("Permission denied: %s - %s", tool_name, e)
            return ToolResult(
                tool_call_id=call_id,
                success=False,
                error=f"Permission denied: {e}",
                duration_ms=round(duration, 2),
            )

        except FileNotFoundError as e:
            duration = (time.perf_counter() - start_time) * 1000
            return ToolResult(
                tool_call_id=call_id,
                success=False,
                error=f"File not found: {e}",
                duration_ms=round(duration, 2),
            )

        except Exception as e:
            duration = (time.perf_counter() - start_time) * 1000
            logger.error(
                "Tool error: %s - %s: %s (agent=%s)",
                tool_name,
                type(e).__name__,
                e,
                agent,
            )
            return ToolResult(
                tool_call_id=call_id,
                success=False,
                error=f"{type(e).__name__}: {e}",
                duration_ms=round(duration, 2),
            )

    def get_tool(self, name: str) -> Optional[ToolDefinition]:
        """Get a tool definition by name.

        Args:
            name: Tool name.

        Returns:
            ToolDefinition or None if not found.
        """
        if name not in self._tools:
            return None

        tool = self._tools[name]
        return ToolDefinition(
            name=tool["name"],
            description=tool["description"],
            parameters=tool["parameters"],
            permission_level=tool["permission"],
        )

    def list_tools(self) -> List[ToolDefinition]:
        """List all registered tools.

        Returns:
            List of ToolDefinition objects.
        """
        return [
            ToolDefinition(
                name=t["name"],
                description=t["description"],
                parameters=t["parameters"],
                permission_level=t["permission"],
            )
            for t in self._tools.values()
        ]

    def list_tool_names(self, role: Optional[str] = None) -> List[str]:
        """List all registered tool names, optionally filtered by role.

        Args:
            role: Optional agent role to filter by (future use).

        Returns:
            Sorted list of tool names.
        """
        # For now, all tools are available to all roles
        # Role-based filtering can be added later
        return sorted(self._tools.keys())

    def list_tools_for_prompt(self) -> str:
        """Format all tools for inclusion in LLM system prompts.

        Returns:
            Formatted string describing available tools for LLM context.
        """
        if not self._tools:
            return "No tools available."

        lines = ["# Available Tools\n"]

        # Group by category
        by_category: Dict[str, List[Dict[str, Any]]] = {}
        for tool in self._tools.values():
            cat = tool["category"]
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(tool)

        for category in sorted(by_category.keys()):
            lines.append(f"## {category.title()}\n")
            for tool in sorted(by_category[category], key=lambda t: t["name"]):
                lines.append(f"### {tool['name']}")
                lines.append(f"  {tool['description']}")
                lines.append(f"  Permission: {tool['permission'].value}")

                if tool["parameters"]:
                    lines.append("  Parameters:")
                    for param_name, param_info in tool["parameters"].items():
                        param_type = param_info.get("type", "any")
                        param_desc = param_info.get("description", "")
                        required = param_info.get("required", False)
                        default = param_info.get("default")

                        req_marker = " (required)" if required else ""
                        default_str = f" [default: {default}]" if default is not None else ""
                        lines.append(f"    - {param_name}: {param_type}{req_marker}{default_str} — {param_desc}")

                lines.append(f"  Returns: {tool['returns']}")
                lines.append("")

        return "\n".join(lines)


def _register_all_tools() -> None:
    """Import and register all tool modules."""
    from tools.file_tools import register_file_tools
    from tools.shell_tools import register_shell_tools
    from tools.code_tools import register_code_tools
    from tools.search_tools import register_search_tools
    from tools.browser_tools import register_browser_tools
    from tools.gui_tools import register_gui_tools
    from tools.batch_tools import register_batch_tools
    from tools.repl_tools import register_repl_tools
    from tools.scratchpad_tools import register_scratchpad_tools
    from tools.dynamic_tools import register_dynamic_tool_tools

    register_file_tools(tool_registry)
    register_shell_tools(tool_registry)
    register_code_tools(tool_registry)
    register_search_tools(tool_registry)
    register_browser_tools(tool_registry)
    register_gui_tools(tool_registry)
    register_batch_tools(tool_registry)
    register_repl_tools(tool_registry)
    register_scratchpad_tools(tool_registry)
    register_dynamic_tool_tools(tool_registry)

    tool_registry._initialized = True
    logger.info("All tools registered: %d tools available", len(tool_registry._tools))


# Singleton instance
tool_registry = ToolRegistry()

# Auto-register all tools on import
_register_all_tools()
