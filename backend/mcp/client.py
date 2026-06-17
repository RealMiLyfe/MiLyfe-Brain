"""Remote MCP Client — Connect to external MCP providers."""

from typing import Any, Optional

import httpx
import structlog

from mcp.schema import MCPToolCall, MCPToolResult, MCPToolSchema

logger = structlog.get_logger()


class MCPClient:
    """Client for connecting to remote MCP providers."""

    def __init__(self, base_url: str, api_key: Optional[str] = None):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self._tools: list[MCPToolSchema] = []

    async def connect(self) -> bool:
        """Connect and discover available tools."""
        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(f"{self.base_url}/tools", headers=headers)
                if resp.status_code == 200:
                    tools_data = resp.json()
                    self._tools = [MCPToolSchema(**t) for t in tools_data]
                    logger.info("MCP client connected", url=self.base_url, tools=len(self._tools))
                    return True
        except Exception as e:
            logger.error("MCP client connection failed", url=self.base_url, error=str(e))

        return False

    async def invoke(self, call: MCPToolCall) -> MCPToolResult:
        """Invoke a tool on the remote MCP server."""
        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    f"{self.base_url}/invoke",
                    json=call.model_dump(),
                    headers=headers,
                )
                if resp.status_code == 200:
                    return MCPToolResult(**resp.json())
                else:
                    return MCPToolResult(
                        tool_name=call.tool_name,
                        success=False,
                        error=f"HTTP {resp.status_code}: {resp.text[:200]}",
                    )
        except Exception as e:
            return MCPToolResult(tool_name=call.tool_name, success=False, error=str(e))

    def list_tools(self) -> list[MCPToolSchema]:
        """List discovered tools."""
        return self._tools
