"""
MiLyfe Brain - Logs Route

Action audit logs: list, filter, export, and statistics.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
from sqlalchemy import func, select

from memory.database import ActionLogRow, async_session_factory
from models.schemas import ActionLog, ActionType, AgentRole, RiskLevel

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/", response_model=List[ActionLog])
async def list_logs(
    playbook_id: Optional[str] = Query(default=None),
    agent_role: Optional[str] = Query(default=None),
    action_type: Optional[str] = Query(default=None),
    risk_level: Optional[str] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
) -> List[ActionLog]:
    """List action logs with optional filters."""
    if async_session_factory is None:
        return []

    async with async_session_factory() as session:
        query = select(ActionLogRow).order_by(ActionLogRow.timestamp.desc())

        if playbook_id:
            query = query.where(ActionLogRow.playbook_id == playbook_id)
        if agent_role:
            query = query.where(ActionLogRow.agent_role == agent_role)
        if action_type:
            query = query.where(ActionLogRow.action_type == action_type)
        if risk_level:
            query = query.where(ActionLogRow.risk_level == risk_level)

        query = query.offset(offset).limit(limit)

        result = await session.execute(query)
        rows = result.scalars().all()

    return [
        ActionLog(
            id=row.id,
            playbook_id=row.playbook_id,
            step_id=row.step_id,
            agent_role=row.agent_role,
            action_type=row.action_type,
            description=row.description,
            details=json.loads(row.details) if row.details else {},
            risk_level=row.risk_level,
            success=row.success,
            timestamp=row.timestamp,
        )
        for row in rows
    ]


@router.get("/export")
async def export_logs(
    days: int = Query(default=7, ge=1, le=90),
) -> JSONResponse:
    """Export logs as JSON for the specified number of days."""
    if async_session_factory is None:
        return JSONResponse(content={"logs": []})

    since = datetime.utcnow() - timedelta(days=days)

    async with async_session_factory() as session:
        result = await session.execute(
            select(ActionLogRow)
            .where(ActionLogRow.timestamp >= since)
            .order_by(ActionLogRow.timestamp.desc())
        )
        rows = result.scalars().all()

    logs = [
        {
            "id": row.id,
            "playbook_id": row.playbook_id,
            "step_id": row.step_id,
            "agent_role": row.agent_role,
            "action_type": row.action_type,
            "description": row.description,
            "details": json.loads(row.details) if row.details else {},
            "risk_level": row.risk_level,
            "success": row.success,
            "timestamp": row.timestamp.isoformat(),
        }
        for row in rows
    ]

    return JSONResponse(
        content={"logs": logs, "count": len(logs), "period_days": days},
        headers={"Content-Disposition": f"attachment; filename=logs_{days}d.json"},
    )


@router.get("/stats")
async def log_statistics(
    days: int = Query(default=7, ge=1, le=90),
) -> Dict[str, Any]:
    """Get log statistics: counts by type, role, risk, and success rate."""
    if async_session_factory is None:
        return {"total": 0}

    since = datetime.utcnow() - timedelta(days=days)

    async with async_session_factory() as session:
        # Total count
        total_result = await session.execute(
            select(func.count(ActionLogRow.id))
            .where(ActionLogRow.timestamp >= since)
        )
        total = total_result.scalar() or 0

        # By action type
        type_result = await session.execute(
            select(ActionLogRow.action_type, func.count(ActionLogRow.id))
            .where(ActionLogRow.timestamp >= since)
            .group_by(ActionLogRow.action_type)
        )
        by_type = {row[0]: row[1] for row in type_result.all()}

        # By role
        role_result = await session.execute(
            select(ActionLogRow.agent_role, func.count(ActionLogRow.id))
            .where(ActionLogRow.timestamp >= since)
            .group_by(ActionLogRow.agent_role)
        )
        by_role = {row[0]: row[1] for row in role_result.all() if row[0]}

        # By risk level
        risk_result = await session.execute(
            select(ActionLogRow.risk_level, func.count(ActionLogRow.id))
            .where(ActionLogRow.timestamp >= since)
            .group_by(ActionLogRow.risk_level)
        )
        by_risk = {row[0]: row[1] for row in risk_result.all()}

        # Success rate
        success_result = await session.execute(
            select(func.count(ActionLogRow.id))
            .where(ActionLogRow.timestamp >= since)
            .where(ActionLogRow.success == True)  # noqa: E712
        )
        success_count = success_result.scalar() or 0

    return {
        "total": total,
        "success_count": success_count,
        "failure_count": total - success_count,
        "success_rate": round(success_count / total * 100, 1) if total > 0 else 100.0,
        "by_type": by_type,
        "by_role": by_role,
        "by_risk": by_risk,
        "period_days": days,
    }
