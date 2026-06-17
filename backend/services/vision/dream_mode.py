"""
Dream Mode - Overnight autonomous processing.

Executes scheduled low-priority tasks during off-hours:
- Code refactoring suggestions
- Documentation updates
- Test generation
- Dependency updates analysis
- Performance optimization suggestions
- Knowledge consolidation (compact memories)
- Workspace cleanup
"""

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class DreamTaskType(str, Enum):
    REFACTOR = "refactor"           # Suggest code improvements
    DOCUMENT = "document"           # Update/generate documentation
    TEST = "test"                   # Generate missing tests
    DEPENDENCY = "dependency"       # Analyze dependency updates
    PERFORMANCE = "performance"     # Profile and suggest optimizations
    CONSOLIDATE = "consolidate"     # Compress and organize memories
    CLEANUP = "cleanup"             # Remove temp files, old logs
    LEARN = "learn"                 # Extract patterns from history
    SECURITY = "security"           # Scan for vulnerabilities


@dataclass
class DreamTask:
    """A task to execute during dream mode."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    task_type: DreamTaskType = DreamTaskType.CLEANUP
    description: str = ""
    priority: int = 5
    max_duration_minutes: int = 30
    payload: Dict[str, Any] = field(default_factory=dict)
    status: str = "pending"
    result: Optional[str] = None
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    error: Optional[str] = None


@dataclass
class DreamSession:
    """A dream mode session (one night's processing)."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    started_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    tasks: List[DreamTask] = field(default_factory=list)
    total_tokens_used: int = 0
    discoveries: List[str] = field(default_factory=list)
    status: str = "running"


class DreamModeService:
    """Manages overnight autonomous processing."""

    def __init__(self):
        self._active_session: Optional[DreamSession] = None
        self._history: List[DreamSession] = []
        self._scheduled_tasks: List[DreamTask] = []
        self._task_handlers: Dict[DreamTaskType, Callable] = {}
        self._config = {
            "enabled": False,
            "start_hour": 2,     # 2 AM
            "end_hour": 6,       # 6 AM
            "max_tokens_per_night": 100000,
            "max_tasks_per_night": 20,
            "quiet_hours_only": True,
        }

    def configure(self, **kwargs):
        """Update dream mode configuration."""
        self._config.update(kwargs)

    def register_handler(self, task_type: DreamTaskType, handler: Callable):
        """Register a handler for a dream task type."""
        self._task_handlers[task_type] = handler

    def schedule_task(self, task_type: DreamTaskType, description: str, priority: int = 5, payload: Dict = None) -> str:
        """Schedule a task for the next dream session."""
        task = DreamTask(
            task_type=task_type,
            description=description,
            priority=priority,
            payload=payload or {},
        )
        self._scheduled_tasks.append(task)
        self._scheduled_tasks.sort(key=lambda t: t.priority)
        return task.id

    async def start_session(self) -> DreamSession:
        """Start a dream mode session."""
        if self._active_session:
            return self._active_session

        session = DreamSession()

        # Add scheduled tasks
        max_tasks = self._config["max_tasks_per_night"]
        session.tasks = self._scheduled_tasks[:max_tasks]
        self._scheduled_tasks = self._scheduled_tasks[max_tasks:]

        # Add default maintenance tasks if space allows
        defaults = [
            DreamTask(task_type=DreamTaskType.CLEANUP, description="Clean temp files and old logs", priority=9),
            DreamTask(task_type=DreamTaskType.CONSOLIDATE, description="Consolidate agent memories", priority=8),
            DreamTask(task_type=DreamTaskType.SECURITY, description="Quick security scan", priority=3),
        ]
        for dt in defaults:
            if len(session.tasks) < max_tasks:
                session.tasks.append(dt)

        self._active_session = session
        return session

    async def execute_session(self):
        """Execute all tasks in the current session."""
        if not self._active_session:
            await self.start_session()

        session = self._active_session
        max_tokens = self._config["max_tokens_per_night"]

        for task in session.tasks:
            # Check token budget
            if session.total_tokens_used >= max_tokens:
                task.status = "skipped"
                continue

            # Check time constraints
            if self._config["quiet_hours_only"] and not self._is_quiet_hours():
                break

            # Execute task
            handler = self._task_handlers.get(task.task_type)
            if handler:
                task.status = "running"
                task.started_at = time.time()
                try:
                    result = await asyncio.wait_for(
                        handler(task.payload),
                        timeout=task.max_duration_minutes * 60,
                    )
                    task.status = "completed"
                    task.result = str(result) if result else "Done"
                    task.completed_at = time.time()

                    # Track discoveries
                    if isinstance(result, dict) and "discovery" in result:
                        session.discoveries.append(result["discovery"])

                except asyncio.TimeoutError:
                    task.status = "timeout"
                    task.error = f"Exceeded {task.max_duration_minutes}min limit"
                except Exception as e:
                    task.status = "failed"
                    task.error = str(e)
            else:
                task.status = "no_handler"

        session.status = "completed"
        session.completed_at = time.time()
        self._history.append(session)
        self._active_session = None

    def _is_quiet_hours(self) -> bool:
        """Check if current time is within quiet hours."""
        current_hour = datetime.now().hour
        start = self._config["start_hour"]
        end = self._config["end_hour"]
        if start < end:
            return start <= current_hour < end
        else:  # Wraps midnight
            return current_hour >= start or current_hour < end

    def get_session_report(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Get a report for a dream session."""
        session = None
        if session_id:
            for s in self._history:
                if s.id == session_id:
                    session = s
                    break
        else:
            session = self._history[-1] if self._history else self._active_session

        if not session:
            return {"status": "no_sessions"}

        return {
            "session_id": session.id,
            "status": session.status,
            "started_at": datetime.fromtimestamp(session.started_at).isoformat(),
            "completed_at": datetime.fromtimestamp(session.completed_at).isoformat() if session.completed_at else None,
            "duration_minutes": round((session.completed_at or time.time()) - session.started_at) / 60,
            "tasks_total": len(session.tasks),
            "tasks_completed": sum(1 for t in session.tasks if t.status == "completed"),
            "tasks_failed": sum(1 for t in session.tasks if t.status == "failed"),
            "tokens_used": session.total_tokens_used,
            "discoveries": session.discoveries,
            "tasks": [
                {"type": t.task_type.value, "description": t.description, "status": t.status, "result": t.result}
                for t in session.tasks
            ],
        }

    @property
    def is_enabled(self) -> bool:
        return self._config["enabled"]

    @property
    def stats(self) -> Dict[str, Any]:
        return {
            "enabled": self._config["enabled"],
            "config": self._config,
            "scheduled_tasks": len(self._scheduled_tasks),
            "sessions_completed": len(self._history),
            "active_session": self._active_session is not None,
        }


# Singleton
dream_service = DreamModeService()
