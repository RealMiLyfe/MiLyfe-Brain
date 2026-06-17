"""Scheduler API — Cron job management."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services.scheduler_service import scheduler

router = APIRouter()


class CreateJobRequest(BaseModel):
    """Request body for creating a scheduled job."""
    playbook_id: str
    cron_expression: str
    title: str


@router.get("/jobs")
async def list_jobs() -> dict:
    """List all scheduled jobs."""
    jobs = await scheduler.list_jobs()
    return {"jobs": [j.model_dump(mode="json") for j in jobs]}


@router.post("/jobs")
async def create_job(body: CreateJobRequest) -> dict:
    """Create a new scheduled job."""
    if not body.playbook_id or not body.cron_expression or not body.title:
        raise HTTPException(status_code=400, detail="All fields required")

    job = await scheduler.add_job(
        playbook_id=body.playbook_id,
        cron_expression=body.cron_expression,
        title=body.title,
    )
    return {"job": job.model_dump(mode="json")}


@router.delete("/jobs/{job_id}")
async def delete_job(job_id: str) -> dict:
    """Delete a scheduled job."""
    success = await scheduler.remove_job(job_id)
    if not success:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"message": "Job deleted", "job_id": job_id}
