"""Notification Service — User-facing alerts and notifications.

Provides creation, listing, marking as read, and WebSocket push
via the event bus.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from memory.database import async_session_factory, NotificationDBModel
from models.schemas import NotificationModel
from agents.message_bus import Topic, get_message_bus

logger = logging.getLogger(__name__)


class NotificationService:
    """Manages user notifications with DB persistence and push delivery.

    Features:
    - Create notifications with type (info, warning, error, success)
    - List all or unread-only notifications
    - Mark all as read
    - Push new notifications via message bus for WebSocket delivery
    """

    def __init__(self) -> None:
        self._bus = get_message_bus()

    async def create(
        self,
        title: str,
        message: str,
        type: str = "info",
    ) -> NotificationModel:
        """Create a new notification.

        Args:
            title: Notification title.
            message: Notification body.
            type: One of info, warning, error, success.

        Returns:
            The created NotificationModel.
        """
        notif_id = str(uuid.uuid4())
        now = datetime.utcnow()

        async with async_session_factory() as db:
            db_notif = NotificationDBModel(
                id=notif_id,
                title=title,
                message=message,
                type=type,
                read=False,
                created_at=now,
            )
            db.add(db_notif)
            await db.commit()

        notif = NotificationModel(
            id=notif_id,
            title=title,
            message=message,
            type=type,
            read=False,
            created_at=now,
        )

        # Push via message bus for WebSocket delivery
        try:
            await self._bus.publish(
                topic=Topic.STATUS_UPDATE,
                payload={
                    "event_type": "notification",
                    "notification": notif.model_dump(mode="json"),
                },
                sender_id="notification_service",
            )
        except Exception as e:
            logger.debug("Failed to push notification: %s", e)

        return notif

    async def list_all(self, unread_only: bool = False) -> List[NotificationModel]:
        """List notifications.

        Args:
            unread_only: If True, only return unread notifications.

        Returns:
            List of NotificationModel instances.
        """
        async with async_session_factory() as db:
            query = select(NotificationDBModel).order_by(
                NotificationDBModel.created_at.desc()
            )
            if unread_only:
                query = query.where(NotificationDBModel.read == False)

            result = await db.execute(query)
            rows = result.scalars().all()

        return [
            NotificationModel(
                id=row.id,
                title=row.title,
                message=row.message,
                type=row.type,
                read=row.read,
                created_at=row.created_at,
            )
            for row in rows
        ]

    async def mark_all_read(self) -> int:
        """Mark all notifications as read.

        Returns:
            Number of notifications marked as read.
        """
        async with async_session_factory() as db:
            result = await db.execute(
                update(NotificationDBModel)
                .where(NotificationDBModel.read == False)
                .values(read=True)
            )
            await db.commit()
            return result.rowcount  # type: ignore


# Singleton
notification_service = NotificationService()
