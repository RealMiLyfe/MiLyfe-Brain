"""MiLyfe Brain — Notification Center Routes."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import List

from fastapi import APIRouter
from sqlalchemy import select, update

from memory.database import NotificationRow, async_session_factory
from models.schemas import Notification

router = APIRouter()


@router.get("/", response_model=List[Notification])
async def get_notifications(unread_only: bool = False, limit: int = 50):
    """Get notifications."""
    async with async_session_factory() as session:
        query = select(NotificationRow).order_by(NotificationRow.created_at.desc()).limit(limit)
        if unread_only:
            query = query.where(NotificationRow.read == False)
        result = await session.execute(query)
        rows = result.scalars().all()
        return [
            Notification(
                id=r.id,
                title=r.title,
                message=r.message,
                type=r.type or "info",
                read=r.read,
                created_at=r.created_at,
            )
            for r in rows
        ]


@router.post("/read-all")
async def mark_all_read():
    """Mark all notifications as read."""
    async with async_session_factory() as session:
        await session.execute(
            update(NotificationRow).where(NotificationRow.read == False).values(read=True)
        )
        await session.commit()
    return {"detail": "All notifications marked as read"}


@router.delete("/{notification_id}")
async def delete_notification(notification_id: str):
    """Delete a notification."""
    async with async_session_factory() as session:
        row = await session.get(NotificationRow, notification_id)
        if row:
            await session.delete(row)
            await session.commit()
    return {"detail": "Deleted"}


async def create_notification(
    title: str,
    message: str,
    type: str = "info",
    data: Optional[dict] = None,
) -> str:
    """Create a new notification (internal helper)."""
    notif_id = str(uuid.uuid4())
    async with async_session_factory() as session:
        session.add(NotificationRow(
            id=notif_id,
            title=title,
            message=message,
            type=type,
            read=False,
            created_at=datetime.utcnow(),
        ))
        await session.commit()
    return notif_id
