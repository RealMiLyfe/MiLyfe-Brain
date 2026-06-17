"""
MiLyfe Brain - Streaming Route

Real-time event streaming via SSE and WebSocket.
Uses asyncio.Queue for event broadcasting.
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from datetime import datetime
from typing import Any, AsyncGenerator, Dict, List, Optional, Set
from uuid import uuid4

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from models.schemas import EventType, StreamEvent

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================
# Event Bus (singleton)
# ============================================================


class EventBus:
    """Pub/sub event bus using asyncio queues for SSE broadcasting."""

    def __init__(self) -> None:
        self._subscribers: List[asyncio.Queue] = []
        self._ws_connections: Set[WebSocket] = set()
        self._event_count: int = 0
        self._lock = asyncio.Lock()

    async def subscribe(self) -> asyncio.Queue:
        """Create a new subscriber queue."""
        queue: asyncio.Queue = asyncio.Queue(maxsize=256)
        async with self._lock:
            self._subscribers.append(queue)
        return queue

    async def unsubscribe(self, queue: asyncio.Queue) -> None:
        """Remove a subscriber queue."""
        async with self._lock:
            if queue in self._subscribers:
                self._subscribers.remove(queue)

    async def publish(self, event: StreamEvent) -> None:
        """Broadcast event to all subscribers."""
        self._event_count += 1
        data = event.model_dump_json()

        async with self._lock:
            dead_queues: List[asyncio.Queue] = []
            for queue in self._subscribers:
                try:
                    queue.put_nowait(data)
                except asyncio.QueueFull:
                    dead_queues.append(queue)

            for dq in dead_queues:
                self._subscribers.remove(dq)

        # Broadcast to WebSocket connections
        dead_ws: List[WebSocket] = []
        for ws in self._ws_connections:
            try:
                await ws.send_text(data)
            except Exception:
                dead_ws.append(ws)

        for dws in dead_ws:
            self._ws_connections.discard(dws)

    def add_ws(self, ws: WebSocket) -> None:
        """Register a WebSocket connection."""
        self._ws_connections.add(ws)

    def remove_ws(self, ws: WebSocket) -> None:
        """Unregister a WebSocket connection."""
        self._ws_connections.discard(ws)

    @property
    def stats(self) -> Dict[str, int]:
        """Connection statistics."""
        return {
            "sse_subscribers": len(self._subscribers),
            "ws_connections": len(self._ws_connections),
            "total_events_published": self._event_count,
        }


event_bus = EventBus()


# ============================================================
# SSE Endpoints
# ============================================================


async def _sse_generator(queue: asyncio.Queue) -> AsyncGenerator[str, None]:
    """Generate SSE formatted events from a queue."""
    try:
        while True:
            try:
                data = await asyncio.wait_for(queue.get(), timeout=30.0)
                yield f"data: {data}\n\n"
            except asyncio.TimeoutError:
                # Send heartbeat
                heartbeat = StreamEvent(
                    event_type=EventType.HEARTBEAT,
                    data={"timestamp": datetime.utcnow().isoformat()},
                )
                yield f"data: {heartbeat.model_dump_json()}\n\n"
    except asyncio.CancelledError:
        pass


@router.get("/sse")
async def sse_stream() -> StreamingResponse:
    """Server-Sent Events stream for all system events."""
    queue = await event_bus.subscribe()

    async def generate():
        try:
            async for event_data in _sse_generator(queue):
                yield event_data
        finally:
            await event_bus.unsubscribe(queue)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/chat")
async def chat_stream(
    session_id: Optional[str] = Query(default=None),
    message: Optional[str] = Query(default=None),
) -> StreamingResponse:
    """Token-by-token SSE chat streaming."""

    async def generate() -> AsyncGenerator[str, None]:
        if not message:
            yield f"data: {json.dumps({'error': 'No message provided'})}\n\n"
            return

        try:
            from tools.llm_client import generate_stream

            async for token in generate_stream(
                messages=[{"role": "user", "content": message}],
            ):
                chunk = {"token": token, "session_id": session_id}
                yield f"data: {json.dumps(chunk)}\n\n"

            yield f"data: {json.dumps({'done': True})}\n\n"

        except ImportError:
            # Fallback if streaming not available
            yield f"data: {json.dumps({'token': 'Streaming not available', 'done': True})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ============================================================
# WebSocket Endpoint
# ============================================================


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """Bidirectional WebSocket for subscribe, approve, ping."""
    await websocket.accept()
    event_bus.add_ws(websocket)

    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
            except json.JSONDecodeError:
                await websocket.send_text(
                    json.dumps({"error": "Invalid JSON"})
                )
                continue

            msg_type = msg.get("type", "")

            if msg_type == "ping":
                await websocket.send_text(
                    json.dumps({"type": "pong", "timestamp": time.time()})
                )

            elif msg_type == "subscribe":
                # Client subscribes to specific event types
                await websocket.send_text(
                    json.dumps({"type": "subscribed", "channels": msg.get("channels", ["all"])})
                )

            elif msg_type == "approve":
                # Handle approval response
                approval_id = msg.get("approval_id")
                approved = msg.get("approved", False)
                await websocket.send_text(
                    json.dumps({
                        "type": "approval_ack",
                        "approval_id": approval_id,
                        "approved": approved,
                    })
                )
                # Publish approval event
                await event_bus.publish(StreamEvent(
                    event_type=EventType.APPROVAL_RESOLVED,
                    data={"approval_id": approval_id, "approved": approved},
                ))

            else:
                await websocket.send_text(
                    json.dumps({"error": f"Unknown message type: {msg_type}"})
                )

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.debug("WebSocket error: %s", e)
    finally:
        event_bus.remove_ws(websocket)


# ============================================================
# Stats Endpoint
# ============================================================


@router.get("/stats")
async def connection_stats() -> Dict[str, Any]:
    """Get current connection statistics."""
    return event_bus.stats
