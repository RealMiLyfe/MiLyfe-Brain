"""Queue Manager — Playbook execution queue.

Sequential execution: one playbook at a time.
Provides enqueue, status, and consumer loop.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections import deque
from typing import Optional

logger = logging.getLogger(__name__)


class QueueManager:
    """Manages a sequential playbook execution queue.

    Only one playbook executes at a time. Additional playbooks
    are queued and processed in FIFO order.
    """

    def __init__(self) -> None:
        self._queue: deque = deque()
        self._running: bool = False
        self._current: Optional[str] = None
        self._completed_count: int = 0
        self._failed_count: int = 0

    async def start(self) -> None:
        """Start the consumer loop."""
        if self._running:
            return

        self._running = True
        logger.info("Queue manager started")

        while self._running:
            try:
                if self._queue and self._current is None:
                    playbook_id = self._queue.popleft()
                    self._current = playbook_id
                    logger.info("Dequeued playbook: %s", playbook_id)

                    try:
                        from graphs.orchestrator import orchestrator
                        await orchestrator.execute_playbook(playbook_id)
                        self._completed_count += 1
                    except Exception as e:
                        logger.error("Playbook %s execution failed: %s", playbook_id, e)
                        self._failed_count += 1
                    finally:
                        self._current = None

                await asyncio.sleep(1)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Queue manager error: %s", e)
                await asyncio.sleep(5)

    def stop(self) -> None:
        """Stop the consumer loop."""
        self._running = False

    async def enqueue(self, playbook_id: str) -> None:
        """Add a playbook to the execution queue.

        Args:
            playbook_id: UUID of the playbook to execute.
        """
        self._queue.append(playbook_id)
        logger.info("Playbook enqueued: %s (queue size: %d)", playbook_id, len(self._queue))

    def status(self) -> dict:
        """Get queue status.

        Returns:
            Dict with running, waiting, and completed counts.
        """
        return {
            "running": self._current,
            "waiting": len(self._queue),
            "completed": self._completed_count,
            "failed": self._failed_count,
            "is_active": self._running,
        }


# Singleton
queue_manager = QueueManager()
