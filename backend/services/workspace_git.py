"""MiLyfe Brain — Workspace Git Integration."""

from __future__ import annotations

import asyncio
from datetime import datetime
from pathlib import Path

import structlog

from config import settings

logger = structlog.get_logger()


class WorkspaceGit:
    """Manages git snapshots of the workspace."""

    def __init__(self):
        self._initialized: bool = False
        self._workspace = Path(settings.workspace_dir)

    async def initialize(self):
        """Initialize git in workspace if not already."""
        if not settings.auto_git_snapshots:
            return

        self._workspace.mkdir(parents=True, exist_ok=True)
        git_dir = self._workspace / ".git"

        if not git_dir.exists():
            proc = await asyncio.create_subprocess_exec(
                "git", "init",
                cwd=str(self._workspace),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await proc.communicate()

            # Configure git
            await asyncio.create_subprocess_exec(
                "git", "config", "user.email", "milyfe@local",
                cwd=str(self._workspace),
                stdout=asyncio.subprocess.PIPE,
            )
            await asyncio.create_subprocess_exec(
                "git", "config", "user.name", "MiLyfe Brain",
                cwd=str(self._workspace),
                stdout=asyncio.subprocess.PIPE,
            )

        self._initialized = True
        logger.info("workspace_git_ready")

    async def snapshot(self, message: str = "auto-snapshot"):
        """Create a git snapshot of the workspace."""
        if not self._initialized or not settings.auto_git_snapshots:
            return

        try:
            # Stage all changes
            proc = await asyncio.create_subprocess_exec(
                "git", "add", "-A",
                cwd=str(self._workspace),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await proc.communicate()

            # Commit
            timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            proc = await asyncio.create_subprocess_exec(
                "git", "commit", "-m", f"[{timestamp}] {message}", "--allow-empty",
                cwd=str(self._workspace),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await proc.communicate()
            logger.debug("workspace_snapshot_created", message=message)
        except Exception as e:
            logger.warning("workspace_snapshot_failed", error=str(e))

    async def get_history(self, limit: int = 20) -> list[dict]:
        """Get recent git history."""
        if not self._initialized:
            return []

        try:
            proc = await asyncio.create_subprocess_exec(
                "git", "log", f"--max-count={limit}", "--format=%H|%s|%ai",
                cwd=str(self._workspace),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await proc.communicate()
            lines = stdout.decode().strip().split("\n")
            return [
                {"hash": p[0], "message": p[1], "date": p[2]}
                for line in lines if line
                for p in [line.split("|", 2)]
                if len(p) == 3
            ]
        except Exception:
            return []


# Singleton
workspace_git = WorkspaceGit()
