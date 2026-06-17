"""MiLyfe Brain — Remote MCP Client.

Connects to remote MCP-compatible servers via HTTP to discover
and invoke tools. Uses httpx for async HTTP communication.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import httpx

from mcp.schema import MCPToolCall, MCPToolResult, MCPToolSchema

logger = logging.getLogger(__name__)

# Default timeout for remote MCP requests
_DEFAULT_TIMEOUT = 30.0


class MCPClient:
    """Client for connecting to remote MCP-compatible servers.

    Discovers available tools and invokes them via HTTP POST requests.
    Handles connection management, retries, and error translation.
    """

    def __init__(self, timeout: float = _DEFAULT_TIMEOUT) -> None:
        self._base_url: Optional[str] = None
        self._timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None
        self._remote_tools: List[MCPToolSchema] = []

    @property
    def is_connected(self) -> bool:
        """Whether the client has an active connection."""
        return self._base_url is not None and self._client is not None

    async def connect(self, url: str) -> None:
        """Connect to a remote MCP server.

        Args:
            url: Base URL of the remote MCP server (e.g., 'http://localhost:9000').

        Raises:
            ConnectionError: If the server is unreachable or returns an error.
        """
        # Normalize URL (remove trailing slash)
        self._base_url = url.rstrip("/")

        # Create HTTP client
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=self._timeout,
            headers={"Content-Type": "application/json"},
        )

        # Verify connectivity by listing tools
        try:
            self._remote_tools = await self._fetch_tools()
            logger.info(
                f"Connected to MCP server at {self._base_url} "
                f"({len(self._remote_tools)} tools available)"
            )
        except Exception as e:
            await self.disconnect()
            raise ConnectionError(
                f"Failed to connect to MCP server at {url}: {e}"
            ) from e

    async def disconnect(self) -> None:
        """Disconnect from the remote MCP server and release resources."""
        if self._client:
            await self._client.aclose()
            self._client = None
        self._base_url = None
        self._remote_tools = []
        logger.info("Disconnected from MCP server")

    async def invoke(self, name: str, arguments: Optional[Dict[str, Any]] = None) -> MCPToolResult:
        """Invoke a tool on the remote MCP server.

        Args:
            name: The name of the tool to invoke.
            arguments: Dict of arguments to pass to the tool.

        Returns:
            MCPToolResult with the result or error.

        Raises:
            RuntimeError: If not connected to a server.
        """
        if not self._client or not self._base_url:
            raise RuntimeError("Not connected to any MCP server. Call connect() first.")

        call = MCPToolCall(name=name, arguments=arguments or {})

        try:
            response = await self._client.post(
                "/tools/invoke",
                json=call.to_dict(),
            )
            response.raise_for_status()

            data = response.json()
            return MCPToolResult.from_dict(data)

        except httpx.TimeoutException:
            return MCPToolResult(
                name=name,
                error=f"Timeout invoking remote tool '{name}' (>{self._timeout}s)",
            )
        except httpx.HTTPStatusError as e:
            return MCPToolResult(
                name=name,
                error=f"HTTP {e.response.status_code} from remote server: {e.response.text[:200]}",
            )
        except httpx.RequestError as e:
            return MCPToolResult(
                name=name,
                error=f"Network error invoking '{name}': {type(e).__name__}: {e}",
            )
        except Exception as e:
            return MCPToolResult(
                name=name,
                error=f"Unexpected error invoking '{name}': {type(e).__name__}: {e}",
            )

    async def list_remote_tools(self) -> List[MCPToolSchema]:
        """List tools available on the remote MCP server.

        Uses cached tools from the last connect/refresh. Call refresh_tools()
        to update the cache.

        Returns:
            List of MCPToolSchema objects available remotely.

        Raises:
            RuntimeError: If not connected to a server.
        """
        if not self._client:
            raise RuntimeError("Not connected to any MCP server. Call connect() first.")

        return list(self._remote_tools)

    async def refresh_tools(self) -> List[MCPToolSchema]:
        """Refresh the cached list of remote tools.

        Returns:
            Updated list of MCPToolSchema objects.

        Raises:
            RuntimeError: If not connected to a server.
        """
        if not self._client:
            raise RuntimeError("Not connected to any MCP server. Call connect() first.")

        self._remote_tools = await self._fetch_tools()
        return list(self._remote_tools)

    async def _fetch_tools(self) -> List[MCPToolSchema]:
        """Fetch the tool list from the remote server.

        Returns:
            List of MCPToolSchema objects.

        Raises:
            ConnectionError: If the request fails.
        """
        if not self._client:
            raise RuntimeError("No HTTP client available")

        try:
            response = await self._client.get("/tools/list")
            response.raise_for_status()
            data = response.json()

            tools: List[MCPToolSchema] = []
            for tool_data in data.get("tools", []):
                try:
                    tools.append(MCPToolSchema.from_dict(tool_data))
                except (KeyError, TypeError) as e:
                    logger.warning(f"Failed to parse remote tool schema: {e}")

            return tools

        except httpx.HTTPStatusError as e:
            raise ConnectionError(
                f"Failed to list tools: HTTP {e.response.status_code}"
            ) from e
        except httpx.RequestError as e:
            raise ConnectionError(
                f"Network error listing tools: {e}"
            ) from e

    async def __aenter__(self) -> MCPClient:
        """Support async context manager usage."""
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Disconnect on context exit."""
        await self.disconnect()
