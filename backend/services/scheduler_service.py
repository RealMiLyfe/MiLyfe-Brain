"""MiLyfe Brain — Cron-Based Scheduler Service."""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Optional

import structlog

logger = structlog.get_logger()


class SchedulerService:
    """Manages scheduled playbook execution via cron expressions."""

    def __init__(self):
        self._running: bool = False
        self._task: Optional[asyncio.Task] = None

    async def start(self):
        """Start the scheduler."""
        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info("scheduler_service_started")

    async def stop(self):
        """Stop the scheduler."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _run_loop(self):
        """Main scheduler loop — checks jobs every 60 seconds."""
        while self._running:
            try:
                await asyncio.sleep(60)
                await self._check_jobs()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("scheduler_error", error=str(e))

    async def _check_jobs(self):
        """Check and execute due jobs."""
        from memory.database import ScheduledJobRow, async_session_factory
        from sqlalchemy import select

        async with async_session_factory() as session:
            result = await session.execute(
                select(ScheduledJobRow).where(ScheduledJobRow.enabled == True)
            )
            jobs = result.scalars().all()

        for job in jobs:
            if self._is_due(job.cron_expression, job.last_run):
                await self._execute_job(job.id, job.playbook_id)

    def _is_due(self, cron_expr: str, last_run: Optional[datetime]) -> bool:
        """Simple cron check (handles @hourly, @daily, @weekly, and basic patterns)."""
        now = datetime.utcnow()
        if not last_run:
            return True  # Never run before

        elapsed = (now - last_run).total_seconds()

        if cron_expr == "@hourly":
            return elapsed >= 3600
        elif cron_expr == "@daily":
            return elapsed >= 86400
        elif cron_expr == "@weekly":
            return elapsed >= 604800
        elif cron_expr == "@monthly":
            return elapsed >= 2592000

        # Basic minute-based cron (check if enough time has passed)
        # Full cron parsing would use a library
        return elapsed >= 3600  # Default to hourly

    async def _execute_job(self, job_id: str, playbook_id: Optional[str]):
        """Execute a scheduled job."""
        if not playbook_id:
            return

        from memory.database import ScheduledJobRow, async_session_factory

        async with async_session_factory() as session:
            job = await session.get(ScheduledJobRow, job_id)
            if job:
                job.last_run = datetime.utcnow()
                await session.commit()

        try:
            from graphs.orchestrator import execute_playbook
            await execute_playbook(playbook_id)
            logger.info("scheduled_job_executed", job_id=job_id, playbook_id=playbook_id)
        except Exception as e:
            logger.error("scheduled_job_failed", job_id=job_id, error=str(e))


# Singleton
scheduler_service = SchedulerService()
