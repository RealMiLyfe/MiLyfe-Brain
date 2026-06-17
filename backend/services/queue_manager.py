"""
MiLyfe Brain - Queue Manager Service

Manages playbook execution queue. Polls for queued playbooks every 2 seconds
and dispatches them to the orchestrator for execution.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Optional

from sqlalchemy import select, update

logger = logging.getLogger(__name__)


class QueueManager:
    """Manages a FIFO execution queue for playbooks."""

    def __init__(self) -> None:
        self._running: bool = False
        self._task: Optional[asyncio.Task] = None
        self._started_at: Optional[datetime] = None
        self._current_playbook_id: Optional[str] = None
        self._processed_count: int = 0

    async def start(self) -> None:
        """Start the queue processing loop."""
        if self._running:
            logger.warning("QueueManager already running")
            return

        self._running = True
        self._started_at = datetime.utcnow()
        self._task = asyncio.create_task(self._process_loop())
        logger.info("QueueManager started")

    async def stop(self) -> None:
        """Stop the queue processing loop gracefully."""
        self._running = False
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        self._started_at = None
        logger.info("QueueManager stopped")

    def get_status(self) -> dict:
        """Return current queue manager status."""
        uptime = 0.0
        if self._started_at:
            uptime = (datetime.utcnow() - self._started_at).total_seconds()

        return {
            "running": self._running,
            "uptime_seconds": uptime,
            "current_playbook_id": self._current_playbook_id,
            "processed_count": self._processed_count,
        }

    async def _process_loop(self) -> None:
        """Main loop: check for queued playbooks every 2 seconds."""
        while self._running:
            try:
                await self._process_next()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("QueueManager loop error: %s", e)

            await asyncio.sleep(2)

    async def _process_next(self) -> None:
        """Pick the oldest queued playbook and dispatch to orchestrator."""
        from memory.database import PlaybookRow, async_session_factory
        from models.schemas import PlaybookStatus

        if async_session_factory is None:
            return

        async with async_session_factory() as session:
            result = await session.execute(
                select(PlaybookRow)
                .where(PlaybookRow.status == PlaybookStatus.QUEUED.value)
                .order_by(PlaybookRow.created_at.asc())
                .limit(1)
            )
            playbook = result.scalar_one_or_none()

            if playbook is None:
                return

            playbook_id = playbook.id
            self._current_playbook_id = playbook_id

            # Mark as running
            await session.execute(
                update(PlaybookRow)
                .where(PlaybookRow.id == playbook_id)
                .values(
                    status=PlaybookStatus.RUNNING.value,
                    updated_at=datetime.utcnow(),
                )
            )
            await session.commit()

        logger.info("Dispatching playbook %s from queue", playbook_id)

        try:
            from graphs.orchestrator import execute_playbook

            await execute_playbook(playbook_id)
            self._processed_count += 1
        except Exception as e:
            logger.error("Playbook %s execution failed: %s", playbook_id, e)

            try:
                async with async_session_factory() as session:
                    await session.execute(
                        update(PlaybookRow)
                        .where(PlaybookRow.id == playbook_id)
                        .values(
                            status=PlaybookStatus.FAILED.value,
                            error=str(e),
                            updated_at=datetime.utcnow(),
                        )
                    )
                    await session.commit()
            except Exception as db_err:
                logger.error("Failed to update playbook status: %s", db_err)
        finally:
            self._current_playbook_id = None


queue_manager = QueueManager()
