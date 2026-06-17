"""Streaming API — WebSocket and SSE for real-time updates."""

import asyncio
import json
import time
from typing import Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from starlette.responses import StreamingResponse

from agents.message_bus import Message, Topic, get_message_bus

router = APIRouter()

# Active WebSocket connections
_ws_connections: Set[WebSocket] = set()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """WebSocket endpoint for real-time agent updates."""
    await websocket.accept()
    _ws_connections.add(websocket)

    bus = get_message_bus()

    # Subscribe to status updates
    async def _on_message(msg: Message) -> None:
        try:
            await websocket.send_json({
                "event": msg.payload.get("event_type", "update"),
                "data": msg.payload,
                "timestamp": msg.timestamp,
            })
        except Exception:
            pass

    sub_id = bus.subscribe(
        topic=Topic.STATUS_UPDATE,
        callback=_on_message,
        subscriber_id=f"ws-{id(websocket)}",
    )

    try:
        while True:
            # Keep connection alive; handle incoming messages
            data = await websocket.receive_text()
            # Client can send ping/pong or commands
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        pass
    finally:
        _ws_connections.discard(websocket)
        bus.unsubscribe(sub_id)


@router.get("/sse")
async def sse_endpoint() -> StreamingResponse:
    """Server-Sent Events endpoint for real-time updates."""
    async def event_generator():
        bus = get_message_bus()
        queue: asyncio.Queue = asyncio.Queue()

        async def _on_message(msg: Message) -> None:
            await queue.put(msg)

        sub_id = bus.subscribe(
            topic=Topic.STATUS_UPDATE,
            callback=_on_message,
            subscriber_id=f"sse-{time.time()}",
        )

        try:
            while True:
                try:
                    msg = await asyncio.wait_for(queue.get(), timeout=30.0)
                    event_data = json.dumps({
                        "event": msg.payload.get("event_type", "update"),
                        "data": msg.payload,
                        "timestamp": msg.timestamp,
                    })
                    yield f"data: {event_data}\n\n"
                except asyncio.TimeoutError:
                    # Send keepalive
                    yield f": keepalive\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            bus.unsubscribe(sub_id)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )



# ─── Approval Endpoints ──────────────────────────────────────────────


@router.post("/approve/{request_id}")
async def approve_action(request_id: str):
    """Approve a pending action request."""
    from safety.approvals import approval_service

    success = approval_service.approve(request_id)
    if not success:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Approval request not found or already resolved")
    return {"status": "approved", "request_id": request_id}


@router.post("/deny/{request_id}")
async def deny_action(request_id: str):
    """Deny a pending action request."""
    from safety.approvals import approval_service

    success = approval_service.deny(request_id)
    if not success:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Approval request not found or already resolved")
    return {"status": "denied", "request_id": request_id}


@router.get("/approvals/pending")
async def list_pending_approvals():
    """List all pending approval requests."""
    from safety.approvals import approval_service

    pending = approval_service.list_pending()
    return [
        {
            "id": r.id,
            "action_type": r.action_type,
            "description": r.description,
            "details": r.details,
            "agent_id": r.agent_id,
            "agent_role": r.agent_role,
            "created_at": r.created_at.isoformat(),
        }
        for r in pending
    ]
