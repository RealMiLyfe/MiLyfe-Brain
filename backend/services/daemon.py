"""MiLyfe Brain — Autonomous Daemon (File Watcher + Processor)."""

from __future__ import annotations

import asyncio
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

import structlog

from config import settings
from models.schemas import DaemonStatus

logger = structlog.get_logger()


class DaemonService:
    """Watches workspace for changes and processes them autonomously."""

    def __init__(self):
        self._running: bool = False
        self._task: Optional[asyncio.Task] = None
        self._events_processed: int = 0
        self._last_event: Optional[datetime] = None
        self._watching: list[str] = []
        self._known_files: set[str] = set()

    async def start(self):
        """Start the daemon."""
        self._running = True
        workspace = Path(settings.workspace_dir)
        workspace.mkdir(parents=True, exist_ok=True)
        self._watching = [str(workspace)]
        self._scan_files()
        self._task = asyncio.create_task(self._watch_loop())
        logger.info("daemon_started", watching=self._watching)

    async def stop(self):
        """Stop the daemon."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    def get_status(self) -> DaemonStatus:
        return DaemonStatus(
            running=self._running,
            watching_paths=self._watching,
            events_processed=self._events_processed,
            last_event=self._last_event,
        )

    def _scan_files(self):
        """Scan workspace for current file state."""
        workspace = Path(settings.workspace_dir)
        self._known_files = set()
        if workspace.exists():
            for f in workspace.rglob("*"):
                if f.is_file():
                    self._known_files.add(str(f))

    async def _watch_loop(self):
        """Poll workspace for changes (simple polling approach)."""
        while self._running:
            try:
                await asyncio.sleep(5)  # Check every 5 seconds
                await self._check_changes()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("daemon_error", error=str(e))
                await asyncio.sleep(10)

    async def _check_changes(self):
        """Check for new/modified/deleted files."""
        workspace = Path(settings.workspace_dir)
        if not workspace.exists():
            return

        current_files = set()
        for f in workspace.rglob("*"):
            if f.is_file() and not any(p.startswith(".") for p in f.relative_to(workspace).parts):
                current_files.add(str(f))

        new_files = current_files - self._known_files
        deleted_files = self._known_files - current_files

        if new_files:
            self._events_processed += len(new_files)
            self._last_event = datetime.utcnow()
            logger.debug("daemon_new_files", count=len(new_files))

        if deleted_files:
            self._events_processed += len(deleted_files)
            self._last_event = datetime.utcnow()

        self._known_files = current_files


# Singleton
daemon_service = DaemonService()
