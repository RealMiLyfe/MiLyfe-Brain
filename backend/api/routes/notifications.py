"""
MiLyfe Brain - Notifications Route

User notification management: list, mark read, delete.
"""
from __future__ import annotations

import logging
from typing import Dict, List

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import delete, select, update

from memory.database import NotificationRow, async_session_factory
from models.schemas import Notification

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/", response_model=List[Notification])
async def list_notifications(
    unread_only: bool = Query(default=False),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> List[Notification]:
    """List notifications, optionally filtering to unread only."""
    if async_session_factory is None:
        return []

    async with async_session_factory() as session:
        query = select(NotificationRow).order_by(NotificationRow.created_at.desc())
        if unread_only:
            query = query.where(NotificationRow.read == False)  # noqa: E712
        query = query.offset(offset).limit(limit)

        result = await session.execute(query)
        rows = result.scalars().all()

    return [
        Notification(
            id=row.id,
            type=row.type,
            title=row.title,
            message=row.message,
            read=row.read,
            playbook_id=row.playbook_id,
            created_at=row.created_at,
        )
        for row in rows
    ]


@router.post("/read-all")
async def mark_all_read() -> Dict[str, int]:
    """Mark all notifications as read."""
    if async_session_factory is None:
        raise HTTPException(status_code=503, detail="Database not available")

    async with async_session_factory() as session:
        result = await session.execute(
            update(NotificationRow)
            .where(NotificationRow.read == False)  # noqa: E712
            .values(read=True)
        )
        await session.commit()
        count = result.rowcount or 0  # type: ignore[union-attr]

    return {"marked_read": count}


@router.delete("/{notification_id}")
async def delete_notification(notification_id: str) -> Dict[str, str]:
    """Delete a notification."""
    if async_session_factory is None:
        raise HTTPException(status_code=503, detail="Database not available")

    async with async_session_factory() as session:
        result = await session.execute(
            select(NotificationRow).where(NotificationRow.id == notification_id)
        )
        if result.scalar_one_or_none() is None:
            raise HTTPException(status_code=404, detail="Notification not found")

        await session.execute(
            delete(NotificationRow).where(NotificationRow.id == notification_id)
        )
        await session.commit()

    return {"status": "deleted", "id": notification_id}
