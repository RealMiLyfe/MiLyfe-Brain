"""MiLyfe Brain — MCP (Model Context Protocol) System.

Provides a local MCP server for registering and invoking tools,
and a client for connecting to remote MCP servers.
"""

from mcp.client import MCPClient
from mcp.schema import MCPToolCall, MCPToolResult, MCPToolSchema
from mcp.server import MCPServer, mcp_server

__all__ = [
    "MCPToolSchema",
    "MCPToolCall",
    "MCPToolResult",
    "MCPServer",
    "mcp_server",
    "MCPClient",
]
