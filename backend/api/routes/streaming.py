"""MiLyfe Brain — WebSocket + SSE Streaming Routes."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime
from typing import AsyncGenerator

import structlog
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sse_starlette.sse import EventSourceResponse

from models.schemas import StreamEvent, EventType

logger = structlog.get_logger()
router = APIRouter()

# Global event bus for broadcasting
_event_subscribers: list[asyncio.Queue] = []


def broadcast_event(event: StreamEvent):
    """Push event to all connected subscribers."""
    event_data = event.model_dump_json()
    for queue in _event_subscribers:
        try:
            queue.put_nowait(event_data)
        except asyncio.QueueFull:
            pass


async def _event_generator() -> AsyncGenerator[str, None]:
    """Generate SSE events."""
    queue: asyncio.Queue = asyncio.Queue(maxsize=100)
    _event_subscribers.append(queue)
    try:
        while True:
            data = await queue.get()
            yield data
    finally:
        _event_subscribers.remove(queue)


@router.get("/sse")
async def sse_stream():
    """Server-Sent Events stream for real-time updates."""
    return EventSourceResponse(_event_generator())


@router.websocket("/ws")
async def websocket_stream(websocket: WebSocket):
    """WebSocket for real-time bidirectional communication."""
    await websocket.accept()
    queue: asyncio.Queue = asyncio.Queue(maxsize=100)
    _event_subscribers.append(queue)

    logger.info("websocket_connected", client=str(websocket.client))

    try:
        while True:
            # Send events to client
            try:
                data = await asyncio.wait_for(queue.get(), timeout=30.0)
                await websocket.send_text(data)
            except asyncio.TimeoutError:
                # Send heartbeat
                await websocket.send_text(json.dumps({
                    "event_type": "heartbeat",
                    "timestamp": datetime.utcnow().isoformat(),
                }))
    except WebSocketDisconnect:
        logger.info("websocket_disconnected", client=str(websocket.client))
    except Exception as e:
        logger.error("websocket_error", error=str(e))
    finally:
        _event_subscribers.remove(queue)


def emit_event(
    event_type: EventType,
    agent_id: str | None = None,
    agent_role: str | None = None,
    data: dict | None = None,
    playbook_id: str | None = None,
):
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
