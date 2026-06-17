"""Logs API — Action log retrieval."""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from memory.database import ActionLogModel, get_db

router = APIRouter()


@router.get("/")
async def get_logs(
    playbook_id: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get action logs, optionally filtered by playbook."""
    query = select(ActionLogModel).order_by(ActionLogModel.timestamp.desc()).limit(limit)

    if playbook_id:
        query = query.where(ActionLogModel.playbook_id == playbook_id)

    result = await db.execute(query)
    rows = result.scalars().all()

    logs = [
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

    return {"logs": logs, "count": len(logs)}
