"""Permission levels per action type."""

from typing import Optional
from config import settings

# Permission level hierarchy: free → notify → approve → blocked
PERMISSION_LEVELS = {
    "free": 0,
    "notify": 1,
    "approve": 2,
    "blocked": 3,
}


async def check_permission(
    required_level: str,
    tool_name: str,
    params: dict,
    agent_id: Optional[str] = None,
    agent_role: Optional[str] = None,
) -> bool:
    """Check if a tool call is permitted.

    Returns True if allowed, False if blocked.
    For 'approve' level, queues an approval request.
    """
    if required_level == "free":
        return True

    if required_level == "blocked":
        return False

    if required_level == "notify":
        # Log prominently but allow
        from api.routes.streaming import broadcast_event
        await broadcast_event(
            "action_notify",
            {"tool": tool_name, "params": params, "agent_id": agent_id, "agent_role": agent_role},
            agent_id=agent_id,
            agent_role=agent_role,
        )
        return True

    if required_level == "approve":
        # Check if approval is required based on settings
        if _needs_approval(tool_name):
            from safety.approvals import request_approval
            approved = await request_approval(tool_name, params, agent_id, agent_role)
            return approved
        return True

    return True


def _needs_approval(tool_name: str) -> bool:
    """Check if tool needs approval based on settings."""
    if tool_name in ("file_delete",) and settings.require_approval_destructive:
        return True
    if tool_name in ("web_browse",) and settings.require_approval_browsing:
        return True
    if tool_name in ("gui_action",) and settings.require_approval_gui:
        return True
    return False
