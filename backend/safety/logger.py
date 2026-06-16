"""Audit Trail Logger — Every tool execution logged."""

import uuid
from datetime import datetime
from typing import Optional

import structlog

logger = structlog.get_logger()


class AuditLogger:
    """Log all tool executions for audit trail."""

    async def log_tool_call(
        self,
        tool_name: str,
        params: dict,
        agent_id: Optional[str] = None,
        agent_role: Optional[str] = None,
        playbook_id: Optional[str] = None,
        result: Optional[str] = None,
    ) -> None:
        """Log a tool call to the database."""
        from memory.database import db

        log_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()

        # Truncate params for storage
        params_str = str(params)[:1000]

        try:
            await db.execute(
                """INSERT INTO action_logs
                   (id, playbook_id, agent_id, agent_role, action_type, description, result, timestamp)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (log_id, playbook_id, agent_id, agent_role, tool_name, params_str, result, now),
            )
        except Exception as e:
            # Don't let logging failures block execution
            logger.warning("Audit log write failed", error=str(e))

        logger.info(
            "Tool executed",
            tool=tool_name,
            agent_role=agent_role,
            agent_id=agent_id,
        )


# Global instance
audit_logger = AuditLogger()
