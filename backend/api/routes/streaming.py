"""MiLyfe Brain — WebSocket + SSE Streaming Routes (token-by-token from Ollama)."""

from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime
from typing import AsyncGenerator, Optional

import httpx
import orjson
import structlog
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from config import settings
from models.schemas import EventType, StreamEvent

logger = structlog.get_logger()
router = APIRouter()

# ─── Global Event Bus ───────────────────────────────────────────
_event_subscribers: list[asyncio.Queue] = []
_subscriber_lock = asyncio.Lock()


def broadcast_event(event: StreamEvent):
    """Push event to all connected subscribers."""
    event_data = event.model_dump_json()
    for queue in _event_subscribers:
        try:
            queue.put_nowait(event_data)
        except asyncio.QueueFull:
            # Drop oldest event to make room
            try:
                queue.get_nowait()
                queue.put_nowait(event_data)
            except asyncio.QueueEmpty:
                pass


def emit_event(
    event_type: EventType,
    agent_id: Optional[str] = None,
    agent_role: Optional[str] = None,
    data: Optional[dict] = None,
    playbook_id: Optional[str] = None,
) -> StreamEvent:
    """Helper to emit a stream event."""
    event = StreamEvent(
        event_type=event_type,
        agent_id=agent_id,
        agent_role=agent_role,
        data=data or {},
        playbook_id=playbook_id,
        timestamp=datetime.utcnow(),
    )
    broadcast_event(event)
    return event


# ─── SSE Event Stream ───────────────────────────────────────────

async def _event_generator() -> AsyncGenerator[str, None]:
    """Generate SSE events from the global bus."""
    queue: asyncio.Queue = asyncio.Queue(maxsize=200)
    _event_subscribers.append(queue)
    try:
        while True:
            data = await queue.get()
            yield data
    except asyncio.CancelledError:
        pass
    finally:
        if queue in _event_subscribers:
            _event_subscribers.remove(queue)


@router.get("/sse")
async def sse_stream():
    """Server-Sent Events stream for real-time updates (all events)."""
    return EventSourceResponse(
        _event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ─── Token-by-Token Streaming Chat ─────────────────────────────

class StreamChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    model: Optional[str] = None


async def _stream_chat_tokens(
    message: str,
    model: Optional[str] = None,
    session_id: Optional[str] = None,
) -> AsyncGenerator[str, None]:
    """Stream tokens from Ollama as SSE events."""
    model = model or settings.default_heavy_model
    session_id = session_id or str(uuid.uuid4())

    # Build messages
    messages = [
        {"role": "system", "content": "You are MiLyfe Brain, a helpful AI assistant with tool access. Be concise and helpful."},
        {"role": "user", "content": message},
    ]

    # Emit start event
    yield json.dumps({
        "type": "start",
        "session_id": session_id,
        "model": model,
    })

    full_response = ""
    token_count = 0

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(300.0, connect=10.0)) as client:
            async with client.stream(
                "POST",
                f"{settings.ollama_base_url}/api/chat",
                json={
                    "model": model,
                    "messages": messages,
                    "stream": True,
                    "options": {"temperature": 0.7, "num_predict": 4096},
                },
            ) as response:
                if response.status_code != 200:
                    yield json.dumps({"type": "error", "content": f"Ollama error: HTTP {response.status_code}"})
                    return

                async for line in response.aiter_lines():
                    if not line:
                        continue
                    try:
                        data = orjson.loads(line)
                        token = data.get("message", {}).get("content", "")
                        done = data.get("done", False)

                        if token:
                            full_response += token
                            token_count += 1
                            yield json.dumps({
                                "type": "token",
                                "content": token,
                                "token_index": token_count,
                            })

                        if done:
                            # Final stats
                            yield json.dumps({
                                "type": "done",
                                "content": full_response,
                                "stats": {
                                    "total_tokens": token_count,
                                    "prompt_tokens": data.get("prompt_eval_count", 0),
                                    "completion_tokens": data.get("eval_count", 0),
                                    "duration_ms": (data.get("total_duration", 0)) / 1_000_000,
                                    "tokens_per_second": data.get("eval_count", 0) / max(data.get("eval_duration", 1) / 1_000_000_000, 0.001),
                                },
                                "session_id": session_id,
                                "model": model,
                            })
                            break

                    except Exception:
                        continue

    except httpx.TimeoutException:
        yield json.dumps({"type": "error", "content": "Request timed out"})
    except Exception as e:
        yield json.dumps({"type": "error", "content": str(e)})


@router.get("/chat")
async def stream_chat(
    message: str = Query(..., description="Message to send"),
    model: Optional[str] = Query(None, description="Model override"),
    session_id: Optional[str] = Query(None, description="Session ID"),
):
    """Stream chat response token-by-token via SSE."""
    return EventSourceResponse(
        _stream_chat_tokens(message, model, session_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ─── Agent Streaming (watch a specific agent think) ─────────────

async def _stream_agent_tokens(agent_id: str) -> AsyncGenerator[str, None]:
    """Stream events for a specific agent."""
    queue: asyncio.Queue = asyncio.Queue(maxsize=200)
    _event_subscribers.append(queue)
    try:
        while True:
            data = await asyncio.wait_for(queue.get(), timeout=60.0)
            event = orjson.loads(data)
            # Filter to this agent only
            if event.get("agent_id") == agent_id:
                yield data
    except (asyncio.TimeoutError, asyncio.CancelledError):
        pass
    finally:
        if queue in _event_subscribers:
            _event_subscribers.remove(queue)


@router.get("/agent/{agent_id}")
async def stream_agent(agent_id: str):
    """Stream events for a specific agent (SSE)."""
    return EventSourceResponse(
        _stream_agent_tokens(agent_id),
        media_type="text/event-stream",
    )


# ─── Playbook Streaming ────────────────────────────────────────

async def _stream_playbook_events(playbook_id: str) -> AsyncGenerator[str, None]:
    """Stream events for a specific playbook."""
    queue: asyncio.Queue = asyncio.Queue(maxsize=200)
    _event_subscribers.append(queue)
    try:
        while True:
            data = await asyncio.wait_for(queue.get(), timeout=120.0)
            event = orjson.loads(data)
            if event.get("playbook_id") == playbook_id or event.get("data", {}).get("playbook_id") == playbook_id:
                yield data
    except (asyncio.TimeoutError, asyncio.CancelledError):
        pass
    finally:
        if queue in _event_subscribers:
            _event_subscribers.remove(queue)


@router.get("/playbook/{playbook_id}")
async def stream_playbook(playbook_id: str):
    """Stream events for a specific playbook execution (SSE)."""
    return EventSourceResponse(
        _stream_playbook_events(playbook_id),
        media_type="text/event-stream",
    )


# ─── WebSocket (Bidirectional) ──────────────────────────────────

@router.websocket("/ws")
async def websocket_stream(websocket: WebSocket):
    """WebSocket for real-time bidirectional communication.

    Client can send:
    - {"type": "subscribe", "filter": "playbook_id" or "agent_id"}
    - {"type": "approve", "approval_id": "...", "approved": true}
    - {"type": "ping"}
    """
    await websocket.accept()
    queue: asyncio.Queue = asyncio.Queue(maxsize=200)
    _event_subscribers.append(queue)

    # Optional filter
    filter_playbook: Optional[str] = None
    filter_agent: Optional[str] = None

    logger.info("websocket_connected", client=str(websocket.client))

    async def send_events():
        """Send events from queue to client."""
        while True:
            try:
                data = await asyncio.wait_for(queue.get(), timeout=25.0)

                # Apply filters if set
                if filter_playbook or filter_agent:
                    event = orjson.loads(data)
                    if filter_playbook and event.get("playbook_id") != filter_playbook:
                        continue
                    if filter_agent and event.get("agent_id") != filter_agent:
                        continue

                await websocket.send_text(data)
            except asyncio.TimeoutError:
                # Heartbeat
                await websocket.send_text(orjson.dumps({
                    "event_type": "heartbeat",
                    "timestamp": datetime.utcnow().isoformat(),
                    "subscribers": len(_event_subscribers),
                }).decode())

    async def receive_commands():
        """Receive commands from client."""
        nonlocal filter_playbook, filter_agent
        while True:
            raw = await websocket.receive_text()
            try:
                msg = orjson.loads(raw)
                msg_type = msg.get("type", "")

                if msg_type == "subscribe":
                    filter_playbook = msg.get("playbook_id")
                    filter_agent = msg.get("agent_id")
                    await websocket.send_text(orjson.dumps({
                        "event_type": "subscribed",
                        "filter": {"playbook_id": filter_playbook, "agent_id": filter_agent},
                    }).decode())

                elif msg_type == "approve":
                    from safety.approvals import resolve_approval
                    resolve_approval(
                        msg.get("approval_id", ""),
                        msg.get("approved", False),
                        msg.get("reason", ""),
                    )

                elif msg_type == "ping":
                    await websocket.send_text(orjson.dumps({"event_type": "pong"}).decode())

                elif msg_type == "unsubscribe":
                    filter_playbook = None
                    filter_agent = None

            except Exception as e:
                logger.debug("ws_command_error", error=str(e))

    try:
        # Run send and receive concurrently
        await asyncio.gather(send_events(), receive_commands())
    except WebSocketDisconnect:
        logger.info("websocket_disconnected", client=str(websocket.client))
    except Exception as e:
        logger.error("websocket_error", error=str(e))
    finally:
        if queue in _event_subscribers:
            _event_subscribers.remove(queue)


# ─── Stats ──────────────────────────────────────────────────────

@router.get("/stats")
async def stream_stats():
    """Get streaming infrastructure stats."""
    return {
        "connected_subscribers": len(_event_subscribers),
        "timestamp": datetime.utcnow().isoformat(),
    }
