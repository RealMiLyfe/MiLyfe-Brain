"""MiLyfe Brain — Scheduled Job Management Routes."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import List

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from memory.database import ScheduledJobRow, async_session_factory
from models.schemas import ScheduledJob, ScheduledJobCreate

router = APIRouter()


@router.get("/jobs", response_model=List[ScheduledJob])
async def list_jobs():
    """List all scheduled jobs."""
    async with async_session_factory() as session:
        result = await session.execute(
            select(ScheduledJobRow).order_by(ScheduledJobRow.created_at.desc())
        )
        rows = result.scalars().all()
        return [
            ScheduledJob(
                id=r.id,
                playbook_id=r.playbook_id,
                title=r.title,
                cron_expression=r.cron_expression,
                enabled=r.enabled,
                last_run=r.last_run,
                next_run=r.next_run,
                created_at=r.created_at,
            )
            for r in rows
        ]


@router.post("/jobs", response_model=ScheduledJob)
async def create_job(data: ScheduledJobCreate):
    """Create a scheduled job."""
    job_id = str(uuid.uuid4())
    async with async_session_factory() as session:
        row = ScheduledJobRow(
            id=job_id,
            playbook_id=data.playbook_id,
            title=data.title,
            cron_expression=data.cron_expression,
            enabled=data.enabled,
            created_at=datetime.utcnow(),
        )
        session.add(row)
        await session.commit()

    return ScheduledJob(
        id=job_id,
        playbook_id=data.playbook_id,
        title=data.title,
        cron_expression=data.cron_expression,
        enabled=data.enabled,
        created_at=datetime.utcnow(),
    )


@router.delete("/jobs/{job_id}")
async def delete_job(job_id: str):
    """Delete a scheduled job."""
    async with async_session_factory() as session:
        row = await session.get(ScheduledJobRow, job_id)
        if not row:
            raise HTTPException(status_code=404, detail="Job not found")
        await session.delete(row)
        await session.commit()
    return {"detail": "Job deleted", "id": job_id}


@router.post("/jobs/{job_id}/toggle")
async def toggle_job(job_id: str):
    """Toggle a job's enabled state."""
    async with async_session_factory() as session:
        row = await session.get(ScheduledJobRow, job_id)
        if not row:
            raise HTTPException(status_code=404, detail="Job not found")
        row.enabled = not row.enabled
        await session.commit()
    return {"detail": f"Job {'enabled' if row.enabled else 'disabled'}", "enabled": row.enabled}
