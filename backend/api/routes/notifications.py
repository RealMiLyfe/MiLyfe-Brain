"""Notification center routes."""

import uuid
from datetime import datetime

from fastapi import APIRouter

from models.schemas import NotificationResponse

router = APIRouter()


@router.get("/", response_model=list[NotificationResponse])
async def get_notifications(unread_only: bool = False, limit: int = 50):
    """Get notifications."""
    from memory.database import db

    if unread_only:
        rows = await db.fetch_all(
            "SELECT * FROM notifications WHERE read = 0 ORDER BY created_at DESC LIMIT ?", (limit,)
        )
    else:
        rows = await db.fetch_all(
            "SELECT * FROM notifications ORDER BY created_at DESC LIMIT ?", (limit,)
        )

    return [
        NotificationResponse(
            id=row["id"],
            title=row["title"],
            message=row["message"],
            type=row["type"],
            read=bool(row["read"]),
            created_at=row["created_at"],
        )
        for row in rows
    ]


@router.post("/read-all")
async def mark_all_read():
    """Mark all notifications as read."""
    from memory.database import db

    await db.execute("UPDATE notifications SET read = 1 WHERE read = 0")
    return {"message": "All notifications marked as read"}


@router.post("/")
async def create_notification(title: str, message: str, type: str = "info"):
    """Create a notification (internal use)."""
    from memory.database import db

    notif_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()

    await db.execute(
        "INSERT INTO notifications (id, title, message, type, read, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (notif_id, title, message, type, 0, now),
    )

    return {"id": notif_id, "message": "Notification created"}


@router.delete("/{notification_id}")
async def delete_notification(notification_id: str):
    """Delete a notification."""
    from memory.database import db

    await db.execute("DELETE FROM notifications WHERE id = ?", (notification_id,))
    return {"message": "Notification deleted"}
