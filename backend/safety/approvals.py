"""Human-in-the-loop approval flow."""

import asyncio
import uuid
from datetime import datetime
from typing import Optional

import structlog

logger = structlog.get_logger()

# Pending approvals
_pending_approvals: dict[str, dict] = {}
_approval_events: dict[str, asyncio.Event] = {}
_approval_results: dict[str, bool] = {}


async def request_approval(
    tool_name: str,
    params: dict,
    agent_id: Optional[str] = None,
    agent_role: Optional[str] = None,
    timeout: float = 300.0,
) -> bool:
    """Request human approval for a tool call.

    Sends approval request via WebSocket and waits for response.
    """
    approval_id = str(uuid.uuid4())
    event = asyncio.Event()

    _pending_approvals[approval_id] = {
        "id": approval_id,
        "tool": tool_name,
        "params": params,
        "agent_id": agent_id,
        "agent_role": agent_role,
        "created_at": datetime.utcnow().isoformat(),
    }
    _approval_events[approval_id] = event

    # Broadcast approval request to frontend
    from api.routes.streaming import broadcast_event
    await broadcast_event(
        "approval_required",
        {
            "approval_id": approval_id,
            "tool": tool_name,
            "params": params,
            "agent_id": agent_id,
            "agent_role": agent_role,
        },
        agent_id=agent_id,
        agent_role=agent_role,
    )

    logger.info("Approval requested", approval_id=approval_id, tool=tool_name)

    # Wait for response with timeout
    try:
        await asyncio.wait_for(event.wait(), timeout=timeout)
        approved = _approval_results.get(approval_id, False)
    except asyncio.TimeoutError:
        logger.warning("Approval timed out", approval_id=approval_id)
        approved = False

    # Cleanup
    _pending_approvals.pop(approval_id, None)
    _approval_events.pop(approval_id, None)
    _approval_results.pop(approval_id, None)

    return approved


async def handle_approval_response(approval_id: str, approved: bool, reason: str = "") -> bool:
    """Handle user's approval response."""
    event = _approval_events.get(approval_id)
    if not event:
        return False

    _approval_results[approval_id] = approved
    event.set()

    logger.info("Approval response", approval_id=approval_id, approved=approved, reason=reason)
    return True


def get_pending_approvals() -> list[dict]:
    """Get all pending approval requests."""
    return list(_pending_approvals.values())
