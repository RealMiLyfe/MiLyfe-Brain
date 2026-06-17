"""MiLyfe Brain — Local MCP Server (exposes tools via MCP protocol)."""

from __future__ import annotations

from typing import Any, Dict, List

import structlog

from mcp.schema import MCPCapabilities, MCPParameter, MCPToolCall, MCPToolResult, MCPToolSchema

logger = structlog.get_logger()


class MCPServer:
    """Local MCP server that exposes the tool registry via MCP protocol."""

    def __init__(self):
        self._tools: Dict[str, MCPToolSchema] = {}

    def register_from_tool_registry(self):
        """Auto-register all tools from the main tool registry."""
        from tools.registry import tool_registry

        for tool_def in tool_registry.list_tools():
            params = []
            for name, type_str in tool_def.parameters.items():
                params.append(MCPParameter(
                    name=name,
                    type=type_str.split()[0] if type_str else "string",
                    description=type_str,
                ))
            self._tools[tool_def.name] = MCPToolSchema(
                name=tool_def.name,
                description=tool_def.description,
                parameters=params,
                returns=tool_def.returns,
            )

    def get_capabilities(self) -> MCPCapabilities:
        """Return server capabilities (tool list)."""
        return MCPCapabilities(
            tools=list(self._tools.values()),
            version="1.0",
            name="milyfe-brain",
        )

    async def handle_call(self, call: MCPToolCall) -> MCPToolResult:
        """Handle an incoming MCP tool call."""
        from tools.registry import tool_registry

        result = await tool_registry.execute(call.tool_name, call.arguments)

        return MCPToolResult(
            request_id=call.request_id,
            success=result.success,
            output=result.output,
            error=result.error,
        )

    def list_tools(self) -> List[MCPToolSchema]:
        """List all available tools."""
        return list(self._tools.values())


# Singleton
mcp_server = MCPServer()
