"""MiLyfe Brain — MCP Client (connect to remote MCP providers)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import httpx
import structlog

from mcp.schema import MCPToolCall, MCPToolResult, MCPToolSchema

logger = structlog.get_logger()


class MCPClient:
    """Connect to remote MCP tool providers."""

    def __init__(self, base_url: str, name: str = "remote"):
        self.base_url = base_url.rstrip("/")
        self.name = name
        self._tools: List[MCPToolSchema] = []

    async def discover(self) -> List[MCPToolSchema]:
        """Discover available tools from remote MCP server."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(f"{self.base_url}/capabilities")
                if resp.status_code == 200:
                    data = resp.json()
                    tools_data = data.get("tools", [])
                    self._tools = [MCPToolSchema(**t) for t in tools_data]
                    logger.info("mcp_discovered", server=self.name, tools=len(self._tools))
                    return self._tools
        except Exception as e:
            logger.error("mcp_discovery_failed", server=self.name, error=str(e))
        return []

    async def call(self, tool_name: str, arguments: Dict[str, Any] = None) -> MCPToolResult:
        """Call a tool on the remote MCP server."""
        call = MCPToolCall(tool_name=tool_name, arguments=arguments or {})

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    f"{self.base_url}/call",
                    json=call.model_dump(),
                )
                if resp.status_code == 200:
                    return MCPToolResult(**resp.json())
                return MCPToolResult(success=False, error=f"HTTP {resp.status_code}")
        except Exception as e:
            return MCPToolResult(success=False, error=str(e))

    @property
    def available_tools(self) -> List[str]:
        return [t.name for t in self._tools]
