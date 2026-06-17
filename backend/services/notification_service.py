"""Notification Service — WebSocket push notifications."""

import uuid
from datetime import datetime
from typing import Optional

import structlog

logger = structlog.get_logger()


class NotificationService:
    """Push notifications via WebSocket."""

    def __init__(self):
        self._started: bool = False

    def start(self) -> None:
        """Start notification service."""
        self._started = True

    async def notify(
        self,
        title: str,
        message: str,
        type: str = "info",
        broadcast: bool = True,
    ) -> str:
        """Create and optionally broadcast a notification."""
        from memory.database import db

        notif_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()

        await db.execute(
            "INSERT INTO notifications (id, title, message, type, read, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (notif_id, title, message, type, 0, now),
        )

        if broadcast:
            from api.routes.streaming import broadcast_event
            await broadcast_event("notification", {
                "id": notif_id,
                "title": title,
                "message": message,
                "type": type,
            })

        return notif_id

    async def handle_approval(self, msg: dict) -> None:
        """Handle approval response from WebSocket."""
        from safety.approvals import handle_approval_response

        approval_id = msg.get("approval_id")
        approved = msg.get("approved", False)
        reason = msg.get("reason", "")

        if approval_id:
            await handle_approval_response(approval_id, approved, reason)


# Global instance
notification_service = NotificationService()
