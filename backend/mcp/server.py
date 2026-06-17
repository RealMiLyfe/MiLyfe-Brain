"""Local MCP Server — Tool registry exposed via MCP protocol."""

import uuid
from typing import Any, Callable

import structlog

from mcp.schema import MCPToolCall, MCPToolResult, MCPToolSchema

logger = structlog.get_logger()


class MCPServer:
    """Local MCP server exposing tool registry."""

    def __init__(self):
        self._tools: dict[str, dict] = {}

    def register_tool(self, schema: MCPToolSchema, handler: Callable) -> None:
        """Register a tool with the MCP server."""
        self._tools[schema.name] = {"schema": schema, "handler": handler}

    def list_tools(self) -> list[MCPToolSchema]:
        """List all registered tools."""
        return [t["schema"] for t in self._tools.values()]

    async def invoke(self, call: MCPToolCall) -> MCPToolResult:
        """Invoke a tool by name."""
        tool_entry = self._tools.get(call.tool_name)
        if not tool_entry:
            return MCPToolResult(
                call_id=call.call_id,
                tool_name=call.tool_name,
                success=False,
                error=f"Unknown tool: {call.tool_name}",
            )

        handler = tool_entry["handler"]
        schema = tool_entry["schema"]

        # Validate required params
        for param in schema.parameters:
            if param.required and param.name not in call.arguments:
                return MCPToolResult(
                    call_id=call.call_id,
                    tool_name=call.tool_name,
                    success=False,
                    error=f"Missing required parameter: {param.name}",
                )

        try:
            import asyncio
            if asyncio.iscoroutinefunction(handler):
                result = await handler(**call.arguments)
            else:
                result = handler(**call.arguments)

            return MCPToolResult(
                call_id=call.call_id or str(uuid.uuid4()),
                tool_name=call.tool_name,
                success=True,
                result=result,
            )
        except Exception as e:
            logger.error("MCP tool invocation failed", tool=call.tool_name, error=str(e))
            return MCPToolResult(
                call_id=call.call_id,
                tool_name=call.tool_name,
                success=False,
                error=str(e),
            )


# Global instance
mcp_server = MCPServer()
