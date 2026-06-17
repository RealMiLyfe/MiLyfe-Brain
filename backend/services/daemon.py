"""Daemon Service — File watcher for the workspace.

Watches the workspace directory for file changes and optionally
triggers auto-processing when new or modified files are detected.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from pathlib import Path
from typing import Dict, Optional, Set

from config import settings

logger = logging.getLogger(__name__)


class DaemonService:
    """Watches workspace for file changes and tracks modifications.

    Uses polling-based file watching (compatible with all platforms
    and containerized environments).
    """

    def __init__(self) -> None:
        self._running: bool = False
        self._task: Optional[asyncio.Task] = None
        self._file_hashes: Dict[str, float] = {}  # path -> mtime
        self._changes: list = []
        self._started_at: Optional[float] = None
        self._poll_interval: float = 5.0  # seconds
        self._watch_dir: str = settings.workspace_dir
        self._ignore_patterns: Set[str] = {
            ".git", "__pycache__", "node_modules", ".venv", ".env"
        }

    async def start(self) -> None:
        """Start the file watcher loop."""
        if self._running:
            return

        self._running = True
        self._started_at = time.time()
        logger.info("Daemon starting, watching: %s", self._watch_dir)

        # Initial scan
        self._file_hashes = self._scan_files()

        while self._running:
            try:
                await asyncio.sleep(self._poll_interval)
                if not self._running:
                    break
                await self._check_changes()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Daemon error: %s", e)
                await asyncio.sleep(10)

    def stop(self) -> None:
        """Stop the file watcher."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
        logger.info("Daemon stopped")

    def status(self) -> dict:
        """Get daemon status."""
        return {
            "running": self._running,
            "watch_dir": self._watch_dir,
            "files_tracked": len(self._file_hashes),
            "changes_detected": len(self._changes),
            "uptime_seconds": (time.time() - self._started_at) if self._started_at else 0,
            "poll_interval": self._poll_interval,
        }

    def _scan_files(self) -> Dict[str, float]:
        """Scan workspace and return file path -> mtime mapping."""
        file_map: Dict[str, float] = {}
        watch_path = Path(self._watch_dir)

        if not watch_path.exists():
            return file_map

        try:
            for root, dirs, files in os.walk(watch_path):
                # Filter ignored directories
                dirs[:] = [d for d in dirs if d not in self._ignore_patterns]

                for filename in files:
                    filepath = os.path.join(root, filename)
                    try:
                        mtime = os.path.getmtime(filepath)
                        file_map[filepath] = mtime
                    except OSError:
                        pass
        except Exception as e:
            logger.warning("Scan error: %s", e)

        return file_map

    async def _check_changes(self) -> None:
        """Check for file changes since last scan."""
        current_files = self._scan_files()

        new_files = set(current_files.keys()) - set(self._file_hashes.keys())
        deleted_files = set(self._file_hashes.keys()) - set(current_files.keys())
        modified_files = {
            f for f in current_files
            if f in self._file_hashes and current_files[f] != self._file_hashes[f]
        }

        for f in new_files:
            self._changes.append({"type": "created", "path": f, "time": time.time()})
            logger.debug("New file: %s", f)

        for f in modified_files:
            self._changes.append({"type": "modified", "path": f, "time": time.time()})
            logger.debug("Modified file: %s", f)

        for f in deleted_files:
            self._changes.append({"type": "deleted", "path": f, "time": time.time()})
            logger.debug("Deleted file: %s", f)

        # Keep only last 500 changes
        if len(self._changes) > 500:
            self._changes = self._changes[-500:]

        self._file_hashes = current_files


# Singleton
daemon_service = DaemonService()
