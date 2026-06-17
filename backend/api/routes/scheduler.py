"""
MiLyfe Brain - Scheduler Route

Scheduled job management: create, list, delete, toggle.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from sqlalchemy import delete, select, update

from memory.database import ScheduledJobRow, async_session_factory
from models.schemas import ScheduledJob, ScheduledJobCreate

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/jobs", response_model=List[ScheduledJob])
async def list_jobs() -> List[ScheduledJob]:
    """List all scheduled jobs."""
    if async_session_factory is None:
        return []

    async with async_session_factory() as session:
        result = await session.execute(
            select(ScheduledJobRow).order_by(ScheduledJobRow.created_at.desc())
        )
        rows = result.scalars().all()

    return [
        ScheduledJob(
            id=row.id,
            name=row.name,
            cron_expression=row.cron_expression,
            playbook_id=row.playbook_id,
            action=row.action or "",
            enabled=row.enabled,
            last_run=row.last_run,
            next_run=row.next_run,
            created_at=row.created_at,
        )
        for row in rows
    ]


@router.post("/jobs", response_model=ScheduledJob)
async def create_job(body: ScheduledJobCreate) -> ScheduledJob:
    """Create a new scheduled job."""
    if async_session_factory is None:
        raise HTTPException(status_code=503, detail="Database not available")

    job_id = str(uuid4())
    now = datetime.utcnow()

    async with async_session_factory() as session:
        row = ScheduledJobRow(
            id=job_id,
            name=body.name,
            cron_expression=body.cron_expression,
            playbook_id=body.playbook_id,
            action=body.action,
            enabled=body.enabled,
            created_at=now,
        )
        session.add(row)
        await session.commit()

    # Notify scheduler service
    try:
        from services.scheduler_service import scheduler_service

        await scheduler_service.reload_jobs()
    except Exception as e:
        logger.warning("Failed to notify scheduler: %s", e)

    return ScheduledJob(
        id=job_id,
        name=body.name,
        cron_expression=body.cron_expression,
        playbook_id=body.playbook_id,
        action=body.action,
        enabled=body.enabled,
        created_at=now,
    )


@router.delete("/jobs/{job_id}")
async def delete_job(job_id: str) -> Dict[str, str]:
    """Delete a scheduled job."""
    if async_session_factory is None:
        raise HTTPException(status_code=503, detail="Database not available")

    async with async_session_factory() as session:
        result = await session.execute(
            select(ScheduledJobRow).where(ScheduledJobRow.id == job_id)
        )
        if result.scalar_one_or_none() is None:
            raise HTTPException(status_code=404, detail="Job not found")

        await session.execute(
            delete(ScheduledJobRow).where(ScheduledJobRow.id == job_id)
        )
        await session.commit()

    return {"status": "deleted", "job_id": job_id}


@router.post("/jobs/{job_id}/toggle")
async def toggle_job(job_id: str) -> Dict[str, Any]:
    """Toggle a scheduled job's enabled state."""
    if async_session_factory is None:
        raise HTTPException(status_code=503, detail="Database not available")

    async with async_session_factory() as session:
        result = await session.execute(
            select(ScheduledJobRow).where(ScheduledJobRow.id == job_id)
        )
        row = result.scalar_one_or_none()
        if row is None:
            raise HTTPException(status_code=404, detail="Job not found")

        new_state = not row.enabled
        await session.execute(
            update(ScheduledJobRow)
            .where(ScheduledJobRow.id == job_id)
            .values(enabled=new_state)
        )
        await session.commit()

    return {"job_id": job_id, "enabled": new_state}
