"""Scheduler Service — Cron-based job scheduling.

Supports standard cron expressions and shortcuts:
@hourly, @daily, @weekly, or "*/5 * * * *"
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from memory.database import async_session_factory, ScheduledJobModel
from models.schemas import ScheduledJob

logger = logging.getLogger(__name__)

# Cron shortcut mappings (in seconds between runs)
CRON_SHORTCUTS = {
    "@hourly": 3600,
    "@daily": 86400,
    "@weekly": 604800,
}


class SchedulerService:
    """Cron-based scheduler that checks and triggers jobs on schedule.

    Supports:
    - Standard cron shortcuts: @hourly, @daily, @weekly
    - Minute-based intervals: */5 * * * * (every 5 minutes)
    """

    def __init__(self) -> None:
        self._running: bool = False
        self._check_interval: float = 30.0  # Check every 30 seconds

    async def start(self) -> None:
        """Start the scheduler loop."""
        if self._running:
            return

        self._running = True
        logger.info("Scheduler started")

        while self._running:
            try:
                await asyncio.sleep(self._check_interval)
                if not self._running:
                    break
                await self._check_jobs()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Scheduler error: %s", e)
                await asyncio.sleep(30)

    def stop(self) -> None:
        """Stop the scheduler."""
        self._running = False

    async def add_job(
        self, playbook_id: str, cron_expression: str, title: str
    ) -> ScheduledJob:
        """Add a new scheduled job.

        Args:
            playbook_id: ID of the playbook to execute.
            cron_expression: Cron expression or shortcut.
            title: Human-readable title for the job.

        Returns:
            The created ScheduledJob model.
        """
        job_id = str(uuid.uuid4())
        next_run = self._calculate_next_run(cron_expression)

        async with async_session_factory() as db:
            job = ScheduledJobModel(
                id=job_id,
                playbook_id=playbook_id,
                title=title,
                cron_expression=cron_expression,
                enabled=True,
                next_run=next_run,
                created_at=datetime.utcnow(),
            )
            db.add(job)
            await db.commit()

        logger.info("Scheduled job added: %s (%s)", title, cron_expression)

        return ScheduledJob(
            id=job_id,
            playbook_id=playbook_id,
            title=title,
            cron_expression=cron_expression,
            enabled=True,
            next_run=next_run,
            created_at=datetime.utcnow(),
        )

    async def remove_job(self, job_id: str) -> bool:
        """Remove a scheduled job by ID."""
        async with async_session_factory() as db:
            result = await db.execute(
                delete(ScheduledJobModel).where(ScheduledJobModel.id == job_id)
            )
            await db.commit()
            deleted = result.rowcount > 0  # type: ignore

        if deleted:
            logger.info("Scheduled job removed: %s", job_id)
        return deleted

    async def list_jobs(self) -> List[ScheduledJob]:
        """List all scheduled jobs."""
        async with async_session_factory() as db:
            result = await db.execute(select(ScheduledJobModel))
            rows = result.scalars().all()

        return [
            ScheduledJob(
                id=row.id,
                playbook_id=row.playbook_id,
                title=row.title,
                cron_expression=row.cron_expression,
                enabled=row.enabled,
                last_run=row.last_run,
                next_run=row.next_run,
                created_at=row.created_at,
            )
            for row in rows
        ]

    async def _check_jobs(self) -> None:
        """Check all enabled jobs and trigger any that are due."""
        now = datetime.utcnow()

        async with async_session_factory() as db:
            result = await db.execute(
                select(ScheduledJobModel).where(
                    ScheduledJobModel.enabled == True,
                    ScheduledJobModel.next_run <= now,
                )
            )
            due_jobs = result.scalars().all()

            for job in due_jobs:
                logger.info("Triggering scheduled job: %s", job.title)

                # Enqueue the playbook
                try:
                    from services.queue_manager import queue_manager
                    await queue_manager.enqueue(job.playbook_id)
                except Exception as e:
                    logger.error("Failed to enqueue job %s: %s", job.id, e)

                # Update job timing
                job.last_run = now
                job.next_run = self._calculate_next_run(job.cron_expression)

            await db.commit()

    def _calculate_next_run(self, cron_expression: str) -> datetime:
        """Calculate the next run time from a cron expression.

        Supports shortcuts and simple interval patterns.
        """
        now = datetime.utcnow()

        # Check shortcuts
        if cron_expression in CRON_SHORTCUTS:
            return now + timedelta(seconds=CRON_SHORTCUTS[cron_expression])

        # Parse simple cron: */N * * * * (every N minutes)
        try:
            parts = cron_expression.strip().split()
            if len(parts) >= 1 and parts[0].startswith("*/"):
                minutes = int(parts[0][2:])
                return now + timedelta(minutes=max(1, minutes))
        except (ValueError, IndexError):
            pass

        # Default: 1 hour from now
        return now + timedelta(hours=1)


# Singleton
scheduler = SchedulerService()
