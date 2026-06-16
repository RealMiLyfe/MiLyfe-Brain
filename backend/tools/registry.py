"""Central Tool Registry — Register, discover, and execute tools."""

import asyncio
from typing import Any, Callable, Optional

import structlog

logger = structlog.get_logger()


class ToolInfo:
    """Metadata about a registered tool."""

    def __init__(self, name: str, description: str, handler: Callable, permission: str = "free", params: dict = None):
        self.name = name
        self.description = description
        self.handler = handler
        self.permission = permission
        self.params = params or {}


class ToolRegistry:
    """Central registry for all agent tools."""

    def __init__(self):
        self._tools: dict[str, ToolInfo] = {}
        self._initialized = False

    def register(self, name: str, description: str, handler: Callable, permission: str = "free", params: dict = None):
        """Register a tool."""
        self._tools[name] = ToolInfo(name, description, handler, permission, params or {})

    def get_tool_info(self, name: str) -> Optional[dict]:
        """Get tool metadata."""
        tool = self._tools.get(name)
        if tool:
            return {"name": tool.name, "description": tool.description, "permission": tool.permission, "params": tool.params}
        return None

    def list_tools(self) -> list[dict]:
        """List all registered tools."""
        return [
            {"name": t.name, "description": t.description, "permission": t.permission}
            for t in self._tools.values()
        ]

    async def execute(self, name: str, params: dict, agent_id: str = None, agent_role: str = None) -> Any:
        """Execute a tool by name with given params."""
        if not self._initialized:
            self._register_all_tools()

        tool = self._tools.get(name)
        if not tool:
            raise ValueError(f"Unknown tool: {name}. Available: {list(self._tools.keys())}")

        # Permission check
        from safety.permissions import check_permission
        allowed = await check_permission(tool.permission, name, params, agent_id, agent_role)
        if not allowed:
            raise PermissionError(f"Tool '{name}' requires '{tool.permission}' permission")

        # Log the execution
        from safety.logger import audit_logger
        await audit_logger.log_tool_call(name, params, agent_id, agent_role)

        # Execute
        if asyncio.iscoroutinefunction(tool.handler):
            result = await tool.handler(**params)
        else:
            result = tool.handler(**params)

        return result

    def _register_all_tools(self):
        """Register all built-in tools."""
        from tools.file_tools import register_file_tools
        from tools.shell_tools import register_shell_tools
        from tools.code_tools import register_code_tools
        from tools.browser_tools import register_browser_tools
        from tools.gui_tools import register_gui_tools
        from tools.search_tools import register_search_tools
        from tools.batch_tools import register_batch_tools
        from tools.repl_tools import register_repl_tools
        from tools.scratchpad_tools import register_scratchpad_tools

        register_file_tools(self)
        register_shell_tools(self)
        register_code_tools(self)
        register_browser_tools(self)
        register_gui_tools(self)
        register_search_tools(self)
        register_batch_tools(self)
        register_repl_tools(self)
        register_scratchpad_tools(self)

        self._initialized = True
        logger.info("Tool registry initialized", tool_count=len(self._tools))


# Global instance
tool_registry = ToolRegistry()
