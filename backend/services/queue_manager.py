"""Queue Manager — Sequential playbook execution queue."""

import asyncio
from datetime import datetime
from typing import Optional

import structlog

from models.schemas import QueueStatus

logger = structlog.get_logger()


class QueueManager:
    """Manage sequential playbook execution queue."""

    def __init__(self):
        self._queue: asyncio.Queue = asyncio.Queue()
        self._running: Optional[dict] = None
        self._completed: list[dict] = []
        self._paused: bool = False
        self._total_processed: int = 0

    async def enqueue(self, playbook_id: str) -> None:
        """Add a playbook to the execution queue."""
        await self._queue.put({
            "playbook_id": playbook_id,
            "queued_at": datetime.utcnow().isoformat(),
        })
        logger.info("Playbook queued", playbook_id=playbook_id)

    async def process_loop(self) -> None:
        """Main processing loop — runs as background task."""
        logger.info("Queue processor started")
        while True:
            try:
                if self._paused:
                    await asyncio.sleep(1)
                    continue

                # Wait for next item
                item = await asyncio.wait_for(self._queue.get(), timeout=5.0)
                playbook_id = item["playbook_id"]

                self._running = {
                    "playbook_id": playbook_id,
                    "started_at": datetime.utcnow().isoformat(),
                }

                # Execute
                from graphs.orchestrator import orchestrator
                result = await orchestrator.execute_playbook(playbook_id)

                self._completed.append({
                    "playbook_id": playbook_id,
                    "status": result.get("status", "unknown"),
                    "completed_at": datetime.utcnow().isoformat(),
                })
                self._total_processed += 1
                self._running = None

                # Keep only last 50 completed
                if len(self._completed) > 50:
                    self._completed = self._completed[-50:]

            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                logger.info("Queue processor cancelled")
                break
            except Exception as e:
                logger.error("Queue processor error", error=str(e))
                self._running = None
                await asyncio.sleep(1)

    def get_status(self) -> QueueStatus:
        """Get current queue status."""
        waiting = []
        try:
            # Peek at queue items
            for i in range(self._queue.qsize()):
                waiting.append({"position": i + 1})
        except Exception:
            pass

        return QueueStatus(
            running=self._running,
            waiting=waiting,
            completed=self._completed[-10:],
            total_processed=self._total_processed,
        )

    def pause(self) -> None:
        self._paused = True
        logger.info("Queue paused")

    def resume(self) -> None:
        self._paused = False
        logger.info("Queue resumed")

    def clear_waiting(self) -> int:
        """Clear waiting items."""
        count = self._queue.qsize()
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except asyncio.QueueEmpty:
                break
        return count


# Global instance
queue_manager = QueueManager()
