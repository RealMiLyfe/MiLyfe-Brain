"""MiLyfe Brain — Permission System."""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

import structlog

from config import settings
from models.schemas import PermissionLevel

logger = structlog.get_logger()


async def check_permission(
    tool_name: str,
    permission: PermissionLevel,
    agent: Any = None,
    arguments: Dict[str, Any] = None,
) -> Tuple[bool, str]:
    """Check if an action is permitted.

    Returns: (allowed: bool, reason: str)
    """
    arguments = arguments or {}

    # Free actions always pass
    if permission == PermissionLevel.FREE:
        return True, "free"

    # Blocked actions never pass
    if permission == PermissionLevel.BLOCKED:
        return False, "Action is blocked by policy"

    # Notify: always allowed, just log prominently
    if permission == PermissionLevel.NOTIFY:
        logger.info(
            "tool_notify",
            tool=tool_name,
            agent_id=agent.id if agent else None,
            args_preview=str(arguments)[:200],
        )
        return True, "notify"

    # Approve: check if approval is required
    if permission == PermissionLevel.APPROVE:
        # Check settings for specific categories
        if tool_name in ("file_delete",) and settings.require_approval_destructive:
            return await _request_approval(tool_name, arguments, agent)
        if tool_name in ("web_browse",) and settings.require_approval_browsing:
            return await _request_approval(tool_name, arguments, agent)
        if tool_name in ("gui_action",) and settings.require_approval_gui:
            return await _request_approval(tool_name, arguments, agent)

        # Default: allow with warning
        logger.warning("tool_auto_approved", tool=tool_name)
        return True, "auto_approved"

    return True, "default_allow"


async def _request_approval(
    tool_name: str,
    arguments: Dict[str, Any],
    agent: Any,
) -> Tuple[bool, str]:
    """Request human approval for a dangerous action.

    For now, auto-approves with a log. Full approval flow requires WebSocket.
    """
    import uuid
    from datetime import datetime
    from models.schemas import ApprovalRequest, RiskLevel, ActionType

    # Create approval request
    request = ApprovalRequest(
        id=str(uuid.uuid4()),
        action_type=_infer_action_type(tool_name),
        description=f"Tool '{tool_name}' requires approval",
        details={"tool": tool_name, "args": arguments},
        agent_id=agent.id if agent else "unknown",
        agent_role=agent.role if agent else "unknown",
        risk_level=RiskLevel.DANGEROUS,
    )

    # Emit approval event
    try:
        from api.routes.streaming import emit_event
        from models.schemas import EventType
        emit_event(
            event_type=EventType.APPROVAL_REQUIRED,
            agent_id=agent.id if agent else None,
            data=request.model_dump(),
        )
    except Exception:
        pass

    # For now, auto-approve (human approval requires WebSocket interaction)
    # In production, this would wait for user response
    logger.warning(
        "auto_approved_dangerous",
        tool=tool_name,
        approval_id=request.id,
    )
    return True, f"auto_approved (approval_id: {request.id})"


def _infer_action_type(tool_name: str):
    """Infer ActionType from tool name."""
    from models.schemas import ActionType

    mapping = {
        "file_read": ActionType.FILE_READ,
        "file_write": ActionType.FILE_WRITE,
        "file_delete": ActionType.FILE_DELETE,
        "shell_exec": ActionType.SHELL_EXEC,
        "web_browse": ActionType.BROWSE_WEB,
        "gui_action": ActionType.GUI_ACTION,
        "code_exec": ActionType.CODE_EXEC,
    }
    return mapping.get(tool_name, ActionType.FILE_READ)
