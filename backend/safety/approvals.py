"""MiLyfe Brain — Human-in-the-Loop Approval Flow."""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime
from typing import Dict, Optional

import structlog

from models.schemas import ApprovalRequest, ApprovalResponse, RiskLevel

logger = structlog.get_logger()

# Pending approvals waiting for user response
_pending_approvals: Dict[str, asyncio.Future] = {}
_approval_requests: Dict[str, ApprovalRequest] = {}


async def request_approval(
    action_type: str,
    description: str,
    details: dict = None,
    agent_id: str = "",
    agent_role: str = "",
    risk_level: RiskLevel = RiskLevel.DANGEROUS,
    timeout: float = 300.0,
) -> bool:
    """Request human approval. Blocks until approved/denied/timeout."""
    request_id = str(uuid.uuid4())

    request = ApprovalRequest(
        id=request_id,
        action_type=action_type,
        description=description,
        details=details or {},
        agent_id=agent_id,
        agent_role=agent_role,
        risk_level=risk_level,
    )

    _approval_requests[request_id] = request

    # Create future to wait on
    future = asyncio.get_event_loop().create_future()
    _pending_approvals[request_id] = future

    # Emit event for UI
    try:
        from api.routes.streaming import emit_event
        from models.schemas import EventType
        emit_event(
            event_type=EventType.APPROVAL_REQUIRED,
            agent_id=agent_id,
            data=request.model_dump(),
        )
    except Exception:
        pass

    # Wait for response
    try:
        approved = await asyncio.wait_for(future, timeout=timeout)
        return approved
    except asyncio.TimeoutError:
        logger.warning("approval_timeout", request_id=request_id)
        return False
    finally:
        _pending_approvals.pop(request_id, None)
        _approval_requests.pop(request_id, None)


def resolve_approval(request_id: str, approved: bool, reason: str = ""):
    """Resolve a pending approval (called from API)."""
    future = _pending_approvals.get(request_id)
    if future and not future.done():
        future.set_result(approved)
        logger.info("approval_resolved", request_id=request_id, approved=approved)
    else:
        logger.warning("approval_not_found", request_id=request_id)


def get_pending_approvals() -> list:
    """Get all pending approval requests."""
    return list(_approval_requests.values())
