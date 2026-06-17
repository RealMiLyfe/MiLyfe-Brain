"""Scheduler Service — Cron-based scheduled playbook execution."""

import asyncio
from datetime import datetime
from typing import Optional

import structlog

logger = structlog.get_logger()


class SchedulerService:
    """Cron-based scheduler for automated playbook execution."""

    def __init__(self):
        self._running: bool = False
        self._check_interval: int = 60  # Check every minute

    async def run(self) -> None:
        """Main scheduler loop."""
        self._running = True
        logger.info("Scheduler service started")

        while self._running:
            try:
                await self._check_scheduled_jobs()
                await asyncio.sleep(self._check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Scheduler error", error=str(e))
                await asyncio.sleep(self._check_interval)

    async def _check_scheduled_jobs(self) -> None:
        """Check for jobs that need to run."""
        from memory.database import db

        try:
            jobs = await db.fetch_all(
                "SELECT * FROM scheduled_jobs WHERE enabled = 1"
            )

            now = datetime.utcnow()

            for job in jobs:
                if self._should_run(job, now):
                    await self._execute_job(job)
        except Exception as e:
            logger.debug("Scheduler check skipped", error=str(e))

    def _should_run(self, job: dict, now: datetime) -> bool:
        """Check if job should run based on cron expression."""
        last_run = job.get("last_run")
        if not last_run:
            return True

        # Simple cron matching (minute-level)
        cron = job.get("cron_expression", "")

        # Handle presets
        if cron == "@hourly":
            interval_minutes = 60
        elif cron == "@daily":
            interval_minutes = 1440
        elif cron == "@weekly":
            interval_minutes = 10080
        else:
            # Default: hourly
            interval_minutes = 60

        try:
            last = datetime.fromisoformat(last_run)
            elapsed = (now - last).total_seconds() / 60
            return elapsed >= interval_minutes
        except (ValueError, TypeError):
            return True

    async def _execute_job(self, job: dict) -> None:
        """Execute a scheduled job."""
        from memory.database import db
        from services.queue_manager import queue_manager

        job_id = job["id"]
        playbook_id = job.get("playbook_id")
        now = datetime.utcnow().isoformat()

        if playbook_id:
            await queue_manager.enqueue(playbook_id)
            logger.info("Scheduled job executed", job_id=job_id, playbook_id=playbook_id)

        # Update last_run
        await db.execute(
            "UPDATE scheduled_jobs SET last_run = ? WHERE id = ?",
            (now, job_id),
        )

    def stop(self) -> None:
        self._running = False


# Global instance
scheduler_service = SchedulerService()
