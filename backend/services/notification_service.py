"""MiLyfe Brain — WebSocket Push Notification Service."""

from __future__ import annotations

import structlog

logger = structlog.get_logger()


class NotificationService:
    """Manages push notifications to connected clients."""

    def __init__(self):
        self._initialized: bool = False

    def initialize(self):
        """Initialize the notification service."""
        self._initialized = True
        logger.info("notification_service_ready")

    async def push(self, title: str, message: str, type: str = "info"):
        """Push a notification to all connected clients."""
        from api.routes.notifications import create_notification
        from api.routes.streaming import emit_event
        from models.schemas import EventType

        await create_notification(title=title, message=message, type=type)
        emit_event(
            event_type=EventType.PROGRESS,
            data={"notification": {"title": title, "message": message, "type": type}},
        )


# Singleton
notification_service = NotificationService()
