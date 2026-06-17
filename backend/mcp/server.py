"""MiLyfe Brain — Local MCP Server.

Registers tools and handles invocation requests locally.
Provides an in-process tool registry that agents can invoke directly.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Coroutine, Dict, List, Optional

from mcp.schema import MCPToolCall, MCPToolResult, MCPToolSchema

logger = logging.getLogger(__name__)

# Type alias for async tool handlers
ToolHandler = Callable[..., Coroutine[Any, Any, Any]]


class MCPServer:
    """Local MCP-compatible tool server.

    Manages tool registration and invocation. Tools are registered
    with their schema and an async handler function. Agents invoke
    tools by name with arguments.
    """

    def __init__(self) -> None:
        self._tools: Dict[str, MCPToolSchema] = {}
        self._handlers: Dict[str, ToolHandler] = {}

    def register_tool(self, schema: MCPToolSchema, handler: ToolHandler) -> None:
        """Register a tool with its schema and handler.

        Args:
            schema: The MCPToolSchema describing the tool.
            handler: Async callable that implements the tool logic.

        Raises:
            ValueError: If a tool with the same name is already registered.
        """
        if schema.name in self._tools:
            raise ValueError(f"Tool '{schema.name}' is already registered")

        self._tools[schema.name] = schema
        self._handlers[schema.name] = handler
        logger.info(f"Registered MCP tool: {schema.name}")

    def unregister_tool(self, name: str) -> bool:
        """Remove a registered tool by name.

        Args:
            name: The tool name to unregister.

        Returns:
            True if the tool was found and removed, False otherwise.
        """
        if name not in self._tools:
            return False

        del self._tools[name]
        del self._handlers[name]
        logger.info(f"Unregistered MCP tool: {name}")
        return True

    async def invoke(self, call: MCPToolCall) -> MCPToolResult:
        """Invoke a registered tool by name.

        Args:
            call: The MCPToolCall specifying tool name and arguments.

        Returns:
            MCPToolResult with the result or error information.
        """
        handler = self._handlers.get(call.name)
        if handler is None:
            return MCPToolResult(
                name=call.name,
                error=f"Tool '{call.name}' is not registered",
            )

        try:
            result = await handler(**call.arguments)
            return MCPToolResult(name=call.name, result=result)
        except TypeError as e:
            return MCPToolResult(
                name=call.name,
                error=f"Invalid arguments for tool '{call.name}': {e}",
            )
        except Exception as e:
            logger.error(f"Tool '{call.name}' execution failed: {e}")
            return MCPToolResult(
                name=call.name,
                error=f"Tool execution failed: {type(e).__name__}: {e}",
            )

    def list_tools(self) -> List[MCPToolSchema]:
        """List all registered tools.

        Returns:
            List of MCPToolSchema objects for all registered tools.
        """
        return list(self._tools.values())

    def get_tool_schema(self, name: str) -> Optional[MCPToolSchema]:
        """Get the schema for a specific tool.

        Args:
            name: The tool name.

        Returns:
            The MCPToolSchema if found, None otherwise.
        """
        return self._tools.get(name)

    def has_tool(self, name: str) -> bool:
        """Check if a tool is registered.

        Args:
            name: The tool name to check.

        Returns:
            True if the tool exists, False otherwise.
        """
        return name in self._tools

    @property
    def tool_count(self) -> int:
        """Number of registered tools."""
        return len(self._tools)


# Singleton instance
mcp_server = MCPServer()
