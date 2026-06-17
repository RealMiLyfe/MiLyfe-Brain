"""MiLyfe Brain — Audit Trail Logger."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, Optional

import structlog

logger = structlog.get_logger()


class AuditLogger:
    """Logs all tool executions and significant actions."""

    async def log_tool_execution(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        output: str = "",
        agent: Any = None,
        playbook_id: Optional[str] = None,
    ):
        """Log a tool execution to the database."""
        try:
            from memory.database import ActionLogRow, async_session_factory
            from safety.command_classifier import classify_command

            # Determine risk level
            risk = "safe"
            if tool_name == "shell_exec":
                cmd = arguments.get("command", "")
                risk = classify_command(cmd)
            elif tool_name in ("file_delete", "web_browse", "gui_action"):
                risk = "caution"

            async with async_session_factory() as session:
                log_entry = ActionLogRow(
                    id=str(uuid.uuid4()),
                    playbook_id=playbook_id,
                    agent_id=agent.id if agent else None,
                    agent_role=agent.role.value if agent and hasattr(agent, "role") else None,
                    action_type=_tool_to_action_type(tool_name),
                    description=f"{tool_name}({_summarize_args(arguments)})",
                    result=output[:500] if output else None,
                    risk_level=risk,
                    timestamp=datetime.utcnow(),
                )
                session.add(log_entry)
                await session.commit()

        except Exception as e:
            logger.debug("audit_log_failed", error=str(e))

    async def log_action(
        self,
        action_type: str,
        description: str,
        agent: Any = None,
        playbook_id: Optional[str] = None,
        risk_level: str = "safe",
    ):
        """Log a general action."""
        try:
            from memory.database import ActionLogRow, async_session_factory

            async with async_session_factory() as session:
                session.add(ActionLogRow(
                    id=str(uuid.uuid4()),
                    playbook_id=playbook_id,
                    agent_id=agent.id if agent else None,
                    agent_role=agent.role.value if agent and hasattr(agent, "role") else None,
                    action_type=action_type,
                    description=description,
                    risk_level=risk_level,
                    timestamp=datetime.utcnow(),
                ))
                await session.commit()
        except Exception:
            pass


def _tool_to_action_type(tool_name: str) -> str:
    """Map tool name to action type."""
    mapping = {
        "file_read": "file_read",
        "file_write": "file_write",
        "file_delete": "file_delete",
        "file_list": "file_read",
        "shell_exec": "shell_exec",
        "code_exec": "code_exec",
        "web_browse": "browse_web",
        "web_search": "browse_web",
        "gui_action": "gui_action",
        "repl_execute": "code_exec",
    }
    return mapping.get(tool_name, "file_read")


def _summarize_args(args: dict) -> str:
    """Create a brief summary of arguments."""
    parts = []
    for k, v in args.items():
        val_str = str(v)
        if len(val_str) > 50:
            val_str = val_str[:50] + "..."
        parts.append(f"{k}={val_str}")
    return ", ".join(parts[:3])


# Singleton
audit_logger = AuditLogger()
