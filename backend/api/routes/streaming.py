"""WebSocket + SSE real-time event streaming."""

import asyncio
import json
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sse_starlette.sse import EventSourceResponse

router = APIRouter()

# In-memory event queue for connected clients
_event_queues: list[asyncio.Queue] = []
_ws_connections: list[WebSocket] = []


async def broadcast_event(event_type: str, data: dict, agent_id: Optional[str] = None, agent_role: Optional[str] = None):
    """Broadcast an event to all connected clients."""
    event = {
        "event_type": event_type,
        "agent_id": agent_id,
        "agent_role": agent_role,
        "data": data,
        "timestamp": datetime.utcnow().isoformat(),
    }

    # Send to SSE clients
    for queue in _event_queues:
        await queue.put(event)

    # Send to WebSocket clients
    disconnected = []
    for ws in _ws_connections:
        try:
            await ws.send_json(event)
        except Exception:
            disconnected.append(ws)

    for ws in disconnected:
        _ws_connections.remove(ws)


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket real-time event stream."""
    await websocket.accept()
    _ws_connections.append(websocket)

    try:
        while True:
            # Keep connection alive, handle incoming messages
            data = await websocket.receive_text()
            # Client can send messages (e.g., approvals)
            try:
                msg = json.loads(data)
                if msg.get("type") == "approval_response":
                    from services.notification_service import notification_service
                    await notification_service.handle_approval(msg)
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        _ws_connections.remove(websocket)


@router.get("/sse")
async def sse_endpoint():
    """SSE event stream."""
    queue: asyncio.Queue = asyncio.Queue()
    _event_queues.append(queue)

    async def event_generator():
        try:
            while True:
                event = await asyncio.wait_for(queue.get(), timeout=30.0)
                yield {"event": event["event_type"], "data": json.dumps(event)}
        except asyncio.TimeoutError:
            yield {"event": "heartbeat", "data": json.dumps({"timestamp": datetime.utcnow().isoformat()})}
        except asyncio.CancelledError:
            pass
        finally:
            _event_queues.remove(queue)

    return EventSourceResponse(event_generator())
