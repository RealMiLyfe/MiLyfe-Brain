"""MiLyfe Brain — Playbook Execution Queue Manager."""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Optional

import structlog
from sqlalchemy import select

from models.schemas import PlaybookStatus, QueueItem, QueueStatus

logger = structlog.get_logger()


class QueueManager:
    """Manages sequential playbook execution."""

    def __init__(self):
        self._running: bool = False
        self._task: Optional[asyncio.Task] = None
        self._current: Optional[str] = None
        self._processed: int = 0

    async def start(self):
        """Start the queue processor."""
        self._running = True
        self._task = asyncio.create_task(self._process_loop())
        logger.info("queue_manager_started")

    async def stop(self):
        """Stop the queue processor."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("queue_manager_stopped")

    async def _process_loop(self):
        """Main processing loop."""
        while self._running:
            try:
                await asyncio.sleep(2)  # Check every 2 seconds
                await self._process_next()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("queue_process_error", error=str(e))
                await asyncio.sleep(5)

    async def _process_next(self):
        """Process next queued playbook."""
        if self._current:
            return  # Already processing

        from memory.database import PlaybookRow, async_session_factory

        async with async_session_factory() as session:
            result = await session.execute(
                select(PlaybookRow)
                .where(PlaybookRow.status == "queued")
                .order_by(PlaybookRow.created_at)
                .limit(1)
            )
            row = result.scalars().first()
            if not row:
                return

            self._current = row.id
            row.status = "running"
            row.started_at = datetime.utcnow()
            await session.commit()

        try:
            from graphs.orchestrator import execute_playbook
            await execute_playbook(self._current)
            self._processed += 1
        except Exception as e:
            logger.error("queue_execution_failed", playbook_id=self._current, error=str(e))
        finally:
            self._current = None

    async def get_status(self) -> QueueStatus:
        """Get current queue status."""
        from memory.database import PlaybookRow, async_session_factory

        async with async_session_factory() as session:
            # Running
            running = None
            if self._current:
                row = await session.get(PlaybookRow, self._current)
                if row:
                    running = QueueItem(
                        playbook_id=row.id,
                        title=row.title,
                        status="running",
                        created_at=row.created_at,
                    )

            # Waiting
            result = await session.execute(
                select(PlaybookRow).where(PlaybookRow.status == "queued").order_by(PlaybookRow.created_at)
            )
            waiting = [
                QueueItem(playbook_id=r.id, title=r.title, status="queued", position=i, created_at=r.created_at)
                for i, r in enumerate(result.scalars().all())
            ]

            # Recently completed
            result2 = await session.execute(
                select(PlaybookRow)
                .where(PlaybookRow.status.in_(["completed", "failed"]))
                .order_by(PlaybookRow.completed_at.desc())
                .limit(10)
            )
            completed = [
                QueueItem(playbook_id=r.id, title=r.title, status=r.status, created_at=r.created_at)
                for r in result2.scalars().all()
            ]

        return QueueStatus(
            running=running,
            waiting=waiting,
            completed=completed,
            total_processed=self._processed,
        )


# Singleton
queue_manager = QueueManager()
