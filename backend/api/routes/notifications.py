"""Notifications API — User-facing alerts."""

from fastapi import APIRouter, Query

from services.notification_service import notification_service

router = APIRouter()


@router.get("/")
async def list_notifications(unread_only: bool = Query(False)) -> dict:
    """List all notifications, optionally filtered to unread only."""
    notifications = await notification_service.list_all(unread_only=unread_only)
    return {
        "notifications": [n.model_dump(mode="json") for n in notifications],
        "count": len(notifications),
    }


@router.post("/read-all")
async def mark_all_read() -> dict:
    """Mark all notifications as read."""
    count = await notification_service.mark_all_read()
    return {"message": "All notifications marked as read", "count": count}
