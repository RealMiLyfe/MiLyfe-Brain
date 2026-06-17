"""
Background job worker for MiLyfe Brain (Phase 3 - Celery/ARQ).

Handles async task execution outside the main API process:
- Playbook execution (long-running)
- Document processing (PDF parsing, embedding)
- Scheduled jobs (cron)
- Email/notification delivery
- Data cleanup and maintenance

Supports two backends:
- ARQ (lightweight, Redis-based) - default
- Celery (enterprise, RabbitMQ/SQS) - optional

Configuration:
    WORKER_BACKEND=arq (arq|celery)
    WORKER_REDIS_URL=redis://localhost:6379/1
    WORKER_CONCURRENCY=4
    WORKER_MAX_RETRIES=3
    WORKER_TASK_TIMEOUT=600
"""

import asyncio
import os
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from .logging_config import get_logger

logger = get_logger("worker")


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    CANCELLED = "cancelled"


class TaskPriority(int, Enum):
    CRITICAL = 1
    HIGH = 3
    NORMAL = 5
    LOW = 7
    BACKGROUND = 9


@dataclass
class Task:
    """Represents a background task."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)
    priority: TaskPriority = TaskPriority.NORMAL
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[Any] = None
    error: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    timeout: int = 600
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    worker_id: Optional[str] = None


class TaskRegistry:
    """Registry of available task handlers."""

    def __init__(self):
        self._handlers: Dict[str, Callable] = {}

    def register(self, name: str, handler: Callable):
        """Register a task handler."""
        self._handlers[name] = handler
        logger.debug(f"Registered task handler: {name}")

    def task(self, name: Optional[str] = None):
        """Decorator to register a task handler."""
        def decorator(func: Callable):
            task_name = name or f"{func.__module__}.{func.__qualname__}"
            self.register(task_name, func)
            func.task_name = task_name
            return func
        return decorator

    def get_handler(self, name: str) -> Optional[Callable]:
        """Get a registered handler."""
        return self._handlers.get(name)

    @property
    def registered_tasks(self) -> List[str]:
        """List all registered task names."""
        return list(self._handlers.keys())


class BackgroundWorker:
    """Background task worker using asyncio + Redis queue."""

    def __init__(self):
        self.redis_url = os.getenv("WORKER_REDIS_URL", "redis://localhost:6379/1")
        self.concurrency = int(os.getenv("WORKER_CONCURRENCY", "4"))
        self.max_retries = int(os.getenv("WORKER_MAX_RETRIES", "3"))
        self.task_timeout = int(os.getenv("WORKER_TASK_TIMEOUT", "600"))
        self.worker_id = f"worker-{uuid.uuid4().hex[:8]}"
        self.registry = TaskRegistry()
        self._running = False
        self._tasks: Dict[str, Task] = {}
        self._queue: asyncio.Queue = asyncio.Queue()

    async def enqueue(
        self,
        task_name: str,
        payload: Dict[str, Any] = None,
        priority: TaskPriority = TaskPriority.NORMAL,
        delay_seconds: int = 0,
    ) -> Task:
        """Add a task to the queue."""
        task = Task(
            name=task_name,
            payload=payload or {},
            priority=priority,
            max_retries=self.max_retries,
            timeout=self.task_timeout,
        )
        self._tasks[task.id] = task

        if delay_seconds > 0:
            asyncio.get_event_loop().call_later(
                delay_seconds, lambda: self._queue.put_nowait(task)
            )
        else:
            await self._queue.put(task)

        logger.info(
            f"Task enqueued: {task_name}",
            extra={"task_id": task.id, "priority": priority.value},
        )
        return task

    async def get_task_status(self, task_id: str) -> Optional[Task]:
        """Get current status of a task."""
        return self._tasks.get(task_id)

    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a pending task."""
        task = self._tasks.get(task_id)
        if task and task.status == TaskStatus.PENDING:
            task.status = TaskStatus.CANCELLED
            return True
        return False

    async def _execute_task(self, task: Task):
        """Execute a single task."""
        handler = self.registry.get_handler(task.name)
        if not handler:
            task.status = TaskStatus.FAILED
            task.error = f"No handler registered for task: {task.name}"
            logger.error(f"Unknown task: {task.name}", extra={"task_id": task.id})
            return

        task.status = TaskStatus.RUNNING
        task.started_at = datetime.utcnow()
        task.worker_id = self.worker_id

        try:
            # Execute with timeout
            if asyncio.iscoroutinefunction(handler):
                result = await asyncio.wait_for(
                    handler(**task.payload),
                    timeout=task.timeout,
                )
            else:
                result = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: handler(**task.payload)
                )

            task.status = TaskStatus.COMPLETED
            task.result = result
            task.completed_at = datetime.utcnow()
            logger.info(
                f"Task completed: {task.name}",
                extra={"task_id": task.id, "duration_ms": (task.completed_at - task.started_at).total_seconds() * 1000},
            )

        except asyncio.TimeoutError:
            task.error = f"Task timed out after {task.timeout}s"
            await self._handle_failure(task)

        except Exception as e:
            task.error = str(e)
            await self._handle_failure(task)

    async def _handle_failure(self, task: Task):
        """Handle task failure with retry logic."""
        task.retry_count += 1

        if task.retry_count <= task.max_retries:
            task.status = TaskStatus.RETRYING
            # Exponential backoff
            delay = min(2 ** task.retry_count * 5, 300)
            logger.warning(
                f"Task failed, retrying in {delay}s: {task.name}",
                extra={"task_id": task.id, "retry": task.retry_count, "error": task.error},
            )
            await asyncio.sleep(delay)
            await self._queue.put(task)
        else:
            task.status = TaskStatus.FAILED
            task.completed_at = datetime.utcnow()
            logger.error(
                f"Task permanently failed: {task.name}",
                extra={"task_id": task.id, "error": task.error},
            )

    async def start(self):
        """Start the worker loop."""
        self._running = True
        logger.info(
            f"Background worker started",
            extra={"worker_id": self.worker_id, "concurrency": self.concurrency},
        )

        # Start consumer tasks
        consumers = [
            asyncio.create_task(self._consumer(i))
            for i in range(self.concurrency)
        ]

        try:
            await asyncio.gather(*consumers)
        except asyncio.CancelledError:
            logger.info("Worker shutting down")
        finally:
            self._running = False

    async def _consumer(self, consumer_id: int):
        """Consumer loop for processing tasks."""
        while self._running:
            try:
                task = await asyncio.wait_for(self._queue.get(), timeout=5.0)
                if task.status != TaskStatus.CANCELLED:
                    await self._execute_task(task)
                self._queue.task_done()
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break

    async def stop(self):
        """Stop the worker gracefully."""
        self._running = False
        logger.info("Worker stopped", extra={"worker_id": self.worker_id})

    @property
    def stats(self) -> Dict[str, Any]:
        """Get worker statistics."""
        status_counts = {}
        for task in self._tasks.values():
            status_counts[task.status.value] = status_counts.get(task.status.value, 0) + 1

        return {
            "worker_id": self.worker_id,
            "running": self._running,
            "concurrency": self.concurrency,
            "queue_size": self._queue.qsize(),
            "total_tasks": len(self._tasks),
            "status_counts": status_counts,
            "registered_handlers": self.registry.registered_tasks,
        }


# Singleton instances
task_registry = TaskRegistry()
worker = BackgroundWorker()
worker.registry = task_registry
