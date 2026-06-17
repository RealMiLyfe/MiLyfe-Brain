"""MiLyfe Brain — Action Log Search/Filter/Export Routes."""

from __future__ import annotations

from typing import List

from fastapi import APIRouter
from sqlalchemy import select

from memory.database import ActionLogRow, async_session_factory
from models.schemas import ActionLog, LogFilter

router = APIRouter()


@router.get("/", response_model=List[ActionLog])
async def get_logs(
    agent_role: Optional[str] = None,
    action_type: Optional[str] = None,
    playbook_id: Optional[str] = None,
    risk_level: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
):
    """Search and filter action logs."""
    async with async_session_factory() as session:
        query = select(ActionLogRow).order_by(ActionLogRow.timestamp.desc())

        if agent_role:
            query = query.where(ActionLogRow.agent_role == agent_role)
        if action_type:
            query = query.where(ActionLogRow.action_type == action_type)
        if playbook_id:
            query = query.where(ActionLogRow.playbook_id == playbook_id)
        if risk_level:
            query = query.where(ActionLogRow.risk_level == risk_level)

        query = query.offset(offset).limit(limit)
        result = await session.execute(query)
        rows = result.scalars().all()

        return [
            ActionLog(
                id=r.id,
                playbook_id=r.playbook_id,
                agent_id=r.agent_id,
                agent_role=r.agent_role,
                action_type=r.action_type,
                description=r.description,
                result=r.result,
                risk_level=r.risk_level or "safe",
                timestamp=r.timestamp,
            )
            for r in rows
        ]


@router.get("/export")
async def export_logs(playbook_id: Optional[str] = None):
    """Export logs as JSON."""
    logs = await get_logs(playbook_id=playbook_id, limit=500)
    return {"logs": [log.model_dump() for log in logs], "count": len(logs)}


@router.get("/stats")
async def log_stats():
    """Get log statistics."""
    async with async_session_factory() as session:
        from sqlalchemy import func
        result = await session.execute(
            select(ActionLogRow.action_type, func.count(ActionLogRow.id))
            .group_by(ActionLogRow.action_type)
        )
        by_type = {r[0]: r[1] for r in result.all()}

        result2 = await session.execute(
            select(ActionLogRow.risk_level, func.count(ActionLogRow.id))
            .group_by(ActionLogRow.risk_level)
        )
        by_risk = {r[0]: r[1] for r in result2.all()}

        total = await session.execute(select(func.count(ActionLogRow.id)))
        total_count = total.scalar() or 0

    return {"total": total_count, "by_type": by_type, "by_risk": by_risk}
