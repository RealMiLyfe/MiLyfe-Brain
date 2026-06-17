"""MiLyfe Brain — Audit Logger.

Records all agent actions to the database for accountability,
debugging, and compliance review.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from memory.database import ActionLogModel, async_session_factory


class AuditLogger:
    """Persists agent action logs to the database.

    Every tool invocation, approval decision, and significant agent
    action is recorded with full context for later audit.
    """

    async def log_action(
        self,
        agent_id: str,
        agent_role: str,
        action_type: str,
        description: str,
        result: Optional[str] = None,
        playbook_id: Optional[str] = None,
    ) -> str:
        """Log an agent action to the database.

        Args:
            agent_id: UUID of the agent performing the action.
            agent_role: Role of the agent (e.g., 'coder', 'reviewer').
            action_type: Category of action (e.g., 'file_write', 'shell_exec').
            description: Human-readable description of what happened.
            result: Optional result or output of the action.
            playbook_id: Optional associated playbook ID.

        Returns:
            The UUID of the created log entry.
        """
        log_id = str(uuid.uuid4())

        async with async_session_factory() as session:
            log_entry = ActionLogModel(
                id=log_id,
                playbook_id=playbook_id,
                agent_id=agent_id,
                agent_role=agent_role,
                action_type=action_type,
                description=description,
                result=result,
                timestamp=datetime.utcnow(),
            )
            session.add(log_entry)
            await session.commit()

        return log_id

    async def get_logs(
        self,
        limit: int = 50,
        offset: int = 0,
        agent_role: Optional[str] = None,
        action_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieve action logs with optional filtering.

        Args:
            limit: Maximum number of logs to return.
            offset: Number of logs to skip (pagination).
            agent_role: Optional filter by agent role.
            action_type: Optional filter by action type.

        Returns:
            List of log entry dicts ordered by timestamp descending.
        """
        async with async_session_factory() as session:
            query = select(ActionLogModel).order_by(ActionLogModel.timestamp.desc())

            if agent_role:
                query = query.where(ActionLogModel.agent_role == agent_role)
            if action_type:
                query = query.where(ActionLogModel.action_type == action_type)

            query = query.limit(limit).offset(offset)
            result = await session.execute(query)
            rows = result.scalars().all()

            return [
                {
                    "id": row.id,
                    "playbook_id": row.playbook_id,
                    "agent_id": row.agent_id,
                    "agent_role": row.agent_role,
                    "action_type": row.action_type,
                    "description": row.description,
                    "result": row.result,
                    "timestamp": row.timestamp.isoformat() if row.timestamp else None,
                }
                for row in rows
            ]

    async def get_log_count(
        self,
        agent_role: Optional[str] = None,
        action_type: Optional[str] = None,
    ) -> int:
        """Get total count of log entries matching filters.

        Args:
            agent_role: Optional filter by agent role.
            action_type: Optional filter by action type.

        Returns:
            Total number of matching log entries.
        """
        from sqlalchemy import func

        async with async_session_factory() as session:
            query = select(func.count(ActionLogModel.id))

            if agent_role:
                query = query.where(ActionLogModel.agent_role == agent_role)
            if action_type:
                query = query.where(ActionLogModel.action_type == action_type)

            result = await session.execute(query)
            return result.scalar() or 0


# Singleton instance
audit_logger = AuditLogger()
