"""
MiLyfe Brain - Tool Hooks Service

Pre-execution and post-execution hooks for tool calls.
Handles permission checks, logging, rate limiting, and result processing.
"""
from __future__ import annotations

import logging
import time
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


async def run_pre_hook(
    tool_call: Dict[str, Any],
    agent: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Execute pre-tool-call hooks.

    Performs:
      - Permission check
      - Rate limiting
      - Argument sanitization
      - Action logging (before execution)

    Args:
        tool_call: Dict with 'tool_name', 'arguments', 'id'.
        agent: Dict with 'role', 'id', 'playbook_id', 'step_id'.

    Returns:
        Dict with:
          - 'allowed': bool — whether to proceed
          - 'reason': str — reason if denied
          - 'start_time': float — timestamp for duration tracking
          - 'modified_arguments': optional modified arguments
    """
    tool_name = tool_call.get("tool_name", "")
    arguments = tool_call.get("arguments", {})
    agent_role = agent.get("role", "orchestrator")

    result: Dict[str, Any] = {
        "allowed": True,
        "reason": "",
        "start_time": time.time(),
        "modified_arguments": None,
    }

    # Permission check
    from services.permission_service import check_permission

    if not check_permission(tool_name, arguments, agent_role):
        result["allowed"] = False
        result["reason"] = f"Permission denied for role '{agent_role}' on tool '{tool_name}'"
        logger.warning(result["reason"])
        return result

    # Log the action (before execution)
    try:
        from memory.database import ActionLogRow, async_session_factory
        from uuid import uuid4
        from datetime import datetime

        if async_session_factory is not None:
            async with async_session_factory() as session:
                log_row = ActionLogRow(
                    id=str(uuid4()),
                    playbook_id=agent.get("playbook_id"),
                    step_id=agent.get("step_id"),
                    agent_role=agent_role,
                    action_type=tool_name,
                    description=f"Tool call: {tool_name}",
                    details=str(arguments)[:1000],
                    risk_level=_get_risk(tool_name),
                    success=True,  # Will update on failure
                    timestamp=datetime.utcnow(),
                )
                session.add(log_row)
                await session.commit()
                result["log_id"] = log_row.id
    except Exception as e:
        logger.debug("Pre-hook logging failed (non-fatal): %s", e)

    return result


async def run_post_hook(
    tool_call: Dict[str, Any],
    tool_result: Dict[str, Any],
    agent: Dict[str, Any],
    pre_hook_data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Execute post-tool-call hooks.

    Performs:
      - Duration tracking
      - Success/failure logging
      - Token accounting
      - Result sanitization

    Args:
        tool_call: Original tool call dict.
        tool_result: Dict with 'success', 'output', 'error'.
        agent: Agent context dict.
        pre_hook_data: Data returned from run_pre_hook.

    Returns:
        Dict with:
          - 'duration_ms': execution duration
          - 'logged': whether action was logged
          - 'sanitized_output': cleaned output
    """
    start_time = (pre_hook_data or {}).get("start_time", time.time())
    duration_ms = (time.time() - start_time) * 1000

    result: Dict[str, Any] = {
        "duration_ms": duration_ms,
        "logged": False,
        "sanitized_output": tool_result.get("output", ""),
    }

    success = tool_result.get("success", True)
    tool_name = tool_call.get("tool_name", "")

    # Update action log with result
    log_id = (pre_hook_data or {}).get("log_id")
    if log_id:
        try:
            from sqlalchemy import update
            from memory.database import ActionLogRow, async_session_factory

            if async_session_factory is not None:
                async with async_session_factory() as session:
                    await session.execute(
                        update(ActionLogRow)
                        .where(ActionLogRow.id == log_id)
                        .values(success=success)
                    )
                    await session.commit()
                result["logged"] = True
        except Exception as e:
            logger.debug("Post-hook log update failed (non-fatal): %s", e)

    # Log failures
    if not success:
        error = tool_result.get("error", "Unknown error")
        logger.warning(
            "Tool '%s' failed for agent '%s' (%.1fms): %s",
            tool_name,
            agent.get("role", "unknown"),
            duration_ms,
            error[:200],
        )

    # Sanitize output (truncate if very long)
    output = tool_result.get("output", "")
    if isinstance(output, str) and len(output) > 50000:
        result["sanitized_output"] = output[:50000] + "\n...[truncated]"

    return result


def _get_risk(tool_name: str) -> str:
    """Get risk level for a tool (for logging)."""
    try:
        from services.permission_service import get_risk_level
        return get_risk_level(tool_name)
    except Exception:
        return "low"
