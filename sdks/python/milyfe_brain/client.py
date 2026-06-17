"""MiLyfe Brain API Client."""

import json
from typing import Any, AsyncGenerator, Dict, List, Optional

import httpx

from .models import (
    AgentRole,
    AgentState,
    ChatMessage,
    HealthResponse,
    Playbook,
    PlaybookCreate,
    StreamEvent,
    TokenStats,
)


class MiLyfeBrainClient:
    """Client for the MiLyfe Brain API.

    Usage:
        client = MiLyfeBrainClient("http://localhost:8200")
        playbook = client.create_playbook(title="My Task", description="Do something")
        status = client.get_playbook_status(playbook.id)

    Async usage:
        async with MiLyfeBrainClient("http://localhost:8200") as client:
            playbook = await client.create_playbook_async(...)
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8200",
        api_key: Optional[str] = None,
        timeout: float = 300.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["X-API-Key"] = api_key

        self._client = httpx.Client(
            base_url=self.base_url,
            headers=headers,
            timeout=timeout,
        )
        self._async_client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        self._async_client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=self._client.headers,
            timeout=self.timeout,
        )
        return self

    async def __aexit__(self, *args):
        if self._async_client:
            await self._async_client.aclose()

    def close(self):
        """Close the sync client."""
        self._client.close()

    def _handle_response(self, response: httpx.Response) -> Any:
        """Handle API response, raising on errors."""
        if response.status_code >= 400:
            detail = response.json().get("detail", response.text)
            raise MiLyfeBrainError(response.status_code, detail)
        if response.status_code == 204:
            return None
        return response.json()

    # ─── Health ────────────────────────────────────────────────────────

    def health(self) -> HealthResponse:
        """Check system health."""
        resp = self._client.get("/health")
        return HealthResponse(**self._handle_response(resp))

    # ─── Playbooks ─────────────────────────────────────────────────────

    def create_playbook(
        self,
        title: str,
        description: str,
        raw_text: Optional[str] = None,
        auto_execute: bool = True,
    ) -> Playbook:
        """Create and optionally execute a playbook."""
        payload = PlaybookCreate(
            title=title,
            description=description,
            raw_text=raw_text,
            auto_execute=auto_execute,
        )
        resp = self._client.post("/api/playbooks/", json=payload.model_dump(exclude_none=True))
        return Playbook(**self._handle_response(resp))

    def list_playbooks(self, status: Optional[str] = None, limit: int = 50) -> List[Playbook]:
        """List all playbooks."""
        params: Dict[str, Any] = {"limit": limit}
        if status:
            params["status"] = status
        resp = self._client.get("/api/playbooks/", params=params)
        return [Playbook(**p) for p in self._handle_response(resp)]

    def get_playbook(self, playbook_id: str) -> Playbook:
        """Get playbook details."""
        resp = self._client.get(f"/api/playbooks/{playbook_id}")
        return Playbook(**self._handle_response(resp))

    def get_playbook_status(self, playbook_id: str) -> Dict[str, Any]:
        """Get real-time execution status."""
        resp = self._client.get(f"/api/playbooks/{playbook_id}/status")
        return self._handle_response(resp)

    def rerun_playbook(self, playbook_id: str) -> Playbook:
        """Re-execute a playbook."""
        resp = self._client.post(f"/api/playbooks/{playbook_id}/rerun")
        return Playbook(**self._handle_response(resp))

    def delete_playbook(self, playbook_id: str) -> None:
        """Delete a playbook."""
        resp = self._client.delete(f"/api/playbooks/{playbook_id}")
        self._handle_response(resp)

    # ─── Agents ────────────────────────────────────────────────────────

    def list_active_agents(self) -> List[AgentState]:
        """List currently active agents."""
        resp = self._client.get("/api/agents/active")
        return [AgentState(**a) for a in self._handle_response(resp)]

    def spawn_agent(self, role: AgentRole, task: str, model: Optional[str] = None) -> AgentState:
        """Spawn a new agent."""
        payload = {"role": role.value, "task": task}
        if model:
            payload["model"] = model
        resp = self._client.post("/api/agents/spawn", json=payload)
        return AgentState(**self._handle_response(resp))

    def retire_agent(self, agent_id: str) -> None:
        """Retire an agent."""
        resp = self._client.delete(f"/api/agents/{agent_id}")
        self._handle_response(resp)

    # ─── Chat ──────────────────────────────────────────────────────────

    def chat(
        self,
        message: str,
        session_id: Optional[str] = None,
        model: Optional[str] = None,
    ) -> ChatMessage:
        """Send a chat message."""
        payload: Dict[str, Any] = {"message": message}
        if session_id:
            payload["session_id"] = session_id
        if model:
            payload["model"] = model
        resp = self._client.post("/api/chat/send", json=payload)
        return ChatMessage(**self._handle_response(resp))

    def get_chat_history(self, session_id: str) -> List[ChatMessage]:
        """Get chat history for a session."""
        resp = self._client.get(f"/api/chat/history/{session_id}")
        return [ChatMessage(**m) for m in self._handle_response(resp)]

    # ─── Documents ─────────────────────────────────────────────────────

    def upload_document(self, file_path: str, collection: str = "default") -> Dict[str, Any]:
        """Upload a document to vector memory."""
        with open(file_path, "rb") as f:
            resp = self._client.post(
                "/api/documents/upload",
                files={"file": f},
                data={"collection": collection},
            )
        return self._handle_response(resp)

    def search_documents(self, query: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """Semantic search documents."""
        resp = self._client.post(
            "/api/documents/search",
            json={"query": query, "n_results": n_results},
        )
        return self._handle_response(resp).get("results", [])

    # ─── Streaming ─────────────────────────────────────────────────────

    def stream_events(self) -> AsyncGenerator[StreamEvent, None]:
        """Stream real-time events via SSE (async generator)."""
        raise NotImplementedError("Use stream_events_async() for SSE streaming")

    async def stream_events_async(self) -> AsyncGenerator[StreamEvent, None]:
        """Stream real-time events via SSE."""
        if not self._async_client:
            raise RuntimeError("Use 'async with' context manager for async operations")

        async with self._async_client.stream("GET", "/api/stream/sse") as response:
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = json.loads(line[6:])
                    yield StreamEvent(**data)

    # ─── Tokens ────────────────────────────────────────────────────────

    def get_token_stats(self, days: int = 7) -> TokenStats:
        """Get token usage statistics."""
        resp = self._client.get("/api/tokens/stats", params={"days": days})
        return TokenStats(**self._handle_response(resp))

    # ─── Settings ──────────────────────────────────────────────────────

    def get_settings(self) -> Dict[str, Any]:
        """Get current settings."""
        resp = self._client.get("/api/settings/")
        return self._handle_response(resp)

    def update_settings(self, settings: Dict[str, Any]) -> None:
        """Update settings."""
        resp = self._client.post("/api/settings/", json=settings)
        self._handle_response(resp)

    # ─── Self-test ─────────────────────────────────────────────────────

    def run_selftest(self) -> Dict[str, Any]:
        """Run full E2E self-test."""
        resp = self._client.post("/api/selftest/run")
        return self._handle_response(resp)


class MiLyfeBrainError(Exception):
    """API error from MiLyfe Brain."""

    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"HTTP {status_code}: {detail}")
