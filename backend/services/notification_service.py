"""
MiLyfe Brain - Notification Service

Manages user notifications (info, success, warning, error, approval).
Persists notifications to the database and provides push capability.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import List, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)


class NotificationService:
    """Service for creating, storing, and retrieving user notifications."""

    def __init__(self) -> None:
        self._initialized: bool = False
        self._in_memory_queue: List[dict] = []

    async def initialize(self) -> None:
        """Initialize the notification service."""
        self._initialized = True
        logger.info("NotificationService initialized")

    async def push(
        self,
        title: str,
        message: str,
        type: str = "info",
        playbook_id: Optional[str] = None,
    ) -> str:
        """
        Push a new notification to the user.

        Args:
            title: Notification title.
            message: Notification body text.
            type: One of 'info', 'success', 'warning', 'error', 'approval'.
            playbook_id: Optional associated playbook ID.

        Returns:
            The notification ID.
        """
        notification_id = str(uuid4())
        now = datetime.utcnow()

        # Persist to database
        try:
            from memory.database import NotificationRow, async_session_factory

            if async_session_factory is not None:
                async with async_session_factory() as session:
                    row = NotificationRow(
                        id=notification_id,
                        type=type,
                        title=title,
                        message=message,
                        read=False,
                        playbook_id=playbook_id,
                        created_at=now,
                    )
                    session.add(row)
                    await session.commit()
            else:
                # Fallback: in-memory queue
                self._in_memory_queue.append({
                    "id": notification_id,
                    "type": type,
                    "title": title,
                    "message": message,
                    "read": False,
                    "playbook_id": playbook_id,
                    "created_at": now.isoformat(),
                })
        except Exception as e:
            logger.error("Failed to persist notification: %s", e)
            self._in_memory_queue.append({
                "id": notification_id,
                "type": type,
                "title": title,
                "message": message,
                "read": False,
                "playbook_id": playbook_id,
                "created_at": now.isoformat(),
            })

        logger.debug("Notification pushed: [%s] %s", type, title)
        return notification_id

    async def get_unread(self, limit: int = 50) -> List[dict]:
        """Retrieve unread notifications."""
        try:
            from sqlalchemy import select

            from memory.database import NotificationRow, async_session_factory

            if async_session_factory is None:
                return self._in_memory_queue[:limit]

            async with async_session_factory() as session:
                result = await session.execute(
                    select(NotificationRow)
                    .where(NotificationRow.read == False)  # noqa: E712
                    .order_by(NotificationRow.created_at.desc())
                    .limit(limit)
                )
                rows = result.scalars().all()
                return [
                    {
                        "id": row.id,
                        "type": row.type,
                        "title": row.title,
                        "message": row.message,
                        "read": row.read,
                        "playbook_id": row.playbook_id,
                        "created_at": row.created_at.isoformat() if row.created_at else None,
                    }
                    for row in rows
                ]
        except Exception as e:
            logger.error("Failed to get unread notifications: %s", e)
            return self._in_memory_queue[:limit]

    async def mark_read(self, notification_id: str) -> bool:
        """Mark a notification as read."""
        try:
            from sqlalchemy import update

            from memory.database import NotificationRow, async_session_factory

            if async_session_factory is None:
                return False

            async with async_session_factory() as session:
                await session.execute(
                    update(NotificationRow)
                    .where(NotificationRow.id == notification_id)
                    .values(read=True)
                )
                await session.commit()
            return True
        except Exception as e:
            logger.error("Failed to mark notification read: %s", e)
            return False


notification_service = NotificationService()
