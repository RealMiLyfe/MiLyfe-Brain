"""Autonomous Daemon — File watcher and auto-processor."""

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
    """Autonomous file watcher + processor."""

    def __init__(self):
        self._running: bool = False
        self._watching: list[str] = []
        self._processed_count: int = 0
        self._last_activity: Optional[str] = None
        self._file_hashes: dict[str, float] = {}

    async def run(self) -> None:
        """Main daemon loop — watches workspace for changes."""
        self._running = True
        self._watching = [settings.workspace_dir]
        logger.info("Daemon started", watching=self._watching)

        while self._running:
            try:
                await self._scan_for_changes()
                await asyncio.sleep(10)  # Check every 10 seconds
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.debug("Daemon scan error", error=str(e))
                await asyncio.sleep(30)

    async def _scan_for_changes(self) -> None:
        """Scan workspace for file changes."""
        workspace = Path(settings.workspace_dir)
        if not workspace.exists():
            return

        skip_dirs = {".git", "node_modules", "__pycache__", ".next", "venv"}
        changed_files = []

        for file_path in workspace.rglob("*"):
            if file_path.is_file():
                parts = file_path.relative_to(workspace).parts
                if any(part in skip_dirs for part in parts):
                    continue

                mtime = file_path.stat().st_mtime
                str_path = str(file_path)

                if str_path in self._file_hashes:
                    if self._file_hashes[str_path] != mtime:
                        changed_files.append(str_path)
                        self._file_hashes[str_path] = mtime
                else:
                    self._file_hashes[str_path] = mtime

        if changed_files:
            self._processed_count += len(changed_files)
            self._last_activity = datetime.utcnow().isoformat()
            logger.debug("Files changed", count=len(changed_files))

    def stop(self) -> None:
        """Stop the daemon."""
        self._running = False
        logger.info("Daemon stopped")

    def get_status(self) -> DaemonStatus:
        """Get daemon status."""
        return DaemonStatus(
            running=self._running,
            watching=self._watching,
            processed_count=self._processed_count,
            last_activity=self._last_activity,
        )


# Global instance
daemon_service = DaemonService()
