"""Scheduler — Cron job management routes."""

import uuid
from datetime import datetime

from fastapi import APIRouter, HTTPException

from models.schemas import ScheduledJobCreate, ScheduledJobResponse

router = APIRouter()


@router.get("/jobs", response_model=list[ScheduledJobResponse])
async def list_scheduled_jobs():
    """List all scheduled jobs."""
    from memory.database import db

    rows = await db.fetch_all("SELECT * FROM scheduled_jobs ORDER BY created_at DESC")
    return [
        ScheduledJobResponse(
            id=row["id"],
            playbook_id=row.get("playbook_id"),
            title=row["title"],
            cron_expression=row["cron_expression"],
            enabled=bool(row["enabled"]),
            last_run=row.get("last_run"),
            next_run=row.get("next_run"),
        )
        for row in rows
    ]


@router.post("/jobs", response_model=ScheduledJobResponse)
async def create_scheduled_job(job: ScheduledJobCreate):
    """Create a new scheduled job."""
    from memory.database import db

    job_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()

    await db.execute(
        """INSERT INTO scheduled_jobs (id, playbook_id, title, cron_expression, enabled, created_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (job_id, job.playbook_id, job.title, job.cron_expression, int(job.enabled), now),
    )

    return ScheduledJobResponse(
        id=job_id,
        playbook_id=job.playbook_id,
        title=job.title,
        cron_expression=job.cron_expression,
        enabled=job.enabled,
    )


@router.put("/jobs/{job_id}")
async def update_scheduled_job(job_id: str, job: ScheduledJobCreate):
    """Update a scheduled job."""
    from memory.database import db

    existing = await db.fetch_one("SELECT * FROM scheduled_jobs WHERE id = ?", (job_id,))
    if not existing:
        raise HTTPException(status_code=404, detail="Job not found")

    await db.execute(
        """UPDATE scheduled_jobs SET title = ?, cron_expression = ?, enabled = ?, playbook_id = ?
           WHERE id = ?""",
        (job.title, job.cron_expression, int(job.enabled), job.playbook_id, job_id),
    )

    return {"message": "Job updated", "id": job_id}


@router.delete("/jobs/{job_id}")
async def delete_scheduled_job(job_id: str):
    """Delete a scheduled job."""
    from memory.database import db

    await db.execute("DELETE FROM scheduled_jobs WHERE id = ?", (job_id,))
    return {"message": "Job deleted", "id": job_id}
