"""
MiLyfe Brain - Scheduler Service

Checks for scheduled jobs every 60 seconds and triggers them when due.
Supports cron-like expressions and shorthand aliases (@hourly, @daily, @weekly).
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select, update

logger = logging.getLogger(__name__)


class SchedulerService:
    """Periodic job scheduler that checks and triggers scheduled playbooks."""

    def __init__(self) -> None:
        self._running: bool = False
        self._task: Optional[asyncio.Task] = None
        self._check_interval: int = 60  # seconds

    async def start(self) -> None:
        """Start the scheduler loop."""
        if self._running:
            logger.warning("SchedulerService already running")
            return

        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info("SchedulerService started (interval=%ds)", self._check_interval)

    async def stop(self) -> None:
        """Stop the scheduler loop."""
        self._running = False
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("SchedulerService stopped")

    async def _run_loop(self) -> None:
        """Main loop: check for due jobs every 60 seconds."""
        while self._running:
            try:
                await self._check_jobs()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Scheduler loop error: %s", e)

            await asyncio.sleep(self._check_interval)

    async def _check_jobs(self) -> None:
        """Query all enabled scheduled jobs and trigger those that are due."""
        from memory.database import ScheduledJobRow, async_session_factory
        from models.schemas import PlaybookStatus

        if async_session_factory is None:
            return

        async with async_session_factory() as session:
            result = await session.execute(
                select(ScheduledJobRow).where(ScheduledJobRow.enabled == True)  # noqa: E712
            )
            jobs = result.scalars().all()

        now = datetime.utcnow()

        for job in jobs:
            try:
                if self._is_due(job.cron_expression, job.last_run):
                    logger.info("Triggering scheduled job: %s", job.name)
                    await self._trigger_job(job.id, job.playbook_id)

                    # Update last_run
                    async with async_session_factory() as session:
                        await session.execute(
                            update(ScheduledJobRow)
                            .where(ScheduledJobRow.id == job.id)
                            .values(last_run=now)
                        )
                        await session.commit()
            except Exception as e:
                logger.error("Error processing job %s: %s", job.name, e)

    def _is_due(self, cron_expr: str, last_run: Optional[datetime]) -> bool:
        """
        Determine if a job is due based on its cron expression and last run time.

        Supports shorthand aliases:
            @hourly  — every 60 minutes
            @daily   — every 24 hours
            @weekly  — every 7 days

        For standard cron expressions (minute hour day month weekday),
        a simplified check is used: compare elapsed time since last_run.
        """
        now = datetime.utcnow()

        # Shorthand aliases
        intervals = {
            "@hourly": timedelta(hours=1),
            "@daily": timedelta(days=1),
            "@weekly": timedelta(weeks=1),
        }

        expr_lower = cron_expr.strip().lower()
        if expr_lower in intervals:
            if last_run is None:
                return True
            return (now - last_run) >= intervals[expr_lower]

        # Standard cron: simplified parsing (minute hour day month weekday)
        # If never run, it's due
        if last_run is None:
            return True

        parts = cron_expr.strip().split()
        if len(parts) != 5:
            logger.warning("Invalid cron expression: %s", cron_expr)
            return False

        minute_expr, hour_expr, day_expr, month_expr, weekday_expr = parts

        # Check minute match
        if minute_expr != "*":
            try:
                if now.minute != int(minute_expr):
                    return False
            except ValueError:
                pass

        # Check hour match
        if hour_expr != "*":
            try:
                if now.hour != int(hour_expr):
                    return False
            except ValueError:
                pass

        # Check day of month
        if day_expr != "*":
            try:
                if now.day != int(day_expr):
                    return False
            except ValueError:
                pass

        # Check month
        if month_expr != "*":
            try:
                if now.month != int(month_expr):
                    return False
            except ValueError:
                pass

        # Check weekday (0=Monday in Python, cron uses 0=Sunday typically)
        if weekday_expr != "*":
            try:
                cron_weekday = int(weekday_expr)
                # Convert cron (0=Sun) to Python (0=Mon)
                python_weekday = (cron_weekday - 1) % 7 if cron_weekday > 0 else 6
                if now.weekday() != python_weekday:
                    return False
            except ValueError:
                pass

        # Avoid running the same job within the same minute
        if last_run and (now - last_run).total_seconds() < 60:
            return False

        return True

    async def _trigger_job(self, job_id: str, playbook_id: Optional[str]) -> None:
        """Trigger a scheduled job by queuing its associated playbook."""
        if playbook_id is None:
            logger.warning("Job %s has no associated playbook", job_id)
            return

        from memory.database import PlaybookRow, async_session_factory
        from models.schemas import PlaybookStatus

        if async_session_factory is None:
            return

        async with async_session_factory() as session:
            await session.execute(
                update(PlaybookRow)
                .where(PlaybookRow.id == playbook_id)
                .values(
                    status=PlaybookStatus.QUEUED.value,
                    updated_at=datetime.utcnow(),
                )
            )
            await session.commit()

        logger.info("Queued playbook %s from scheduled job %s", playbook_id, job_id)


scheduler_service = SchedulerService()
