"""
MiLyfe Brain - Workspace Git Service

Manages git operations for the workspace directory using asyncio subprocess.
Provides snapshot and history functionality for version control.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class WorkspaceGit:
    """Git operations manager for the workspace."""

    def __init__(self) -> None:
        self._workspace: Optional[Path] = None
        self._initialized: bool = False

    async def initialize(self) -> None:
        """Initialize git in the workspace if not already initialized."""
        from config import settings

        self._workspace = Path(settings.workspace_dir).resolve()

        if not self._workspace.exists():
            self._workspace.mkdir(parents=True, exist_ok=True)

        # Check if git is already initialized
        git_dir = self._workspace / ".git"
        if not git_dir.exists():
            await self._run_git("init")
            await self._run_git("config", "user.email", "milyfe@local")
            await self._run_git("config", "user.name", "MiLyfe Brain")
            # Initial commit
            await self._run_git("add", "-A")
            await self._run_git("commit", "--allow-empty", "-m", "Initial workspace state")
            logger.info("Git initialized in workspace: %s", self._workspace)
        else:
            logger.info("Git already initialized in workspace: %s", self._workspace)

        self._initialized = True

    async def snapshot(self, message: Optional[str] = None) -> Optional[str]:
        """
        Create a git snapshot (add all + commit).

        Args:
            message: Commit message. Defaults to timestamped auto-snapshot message.

        Returns:
            The commit hash on success, None on failure.
        """
        if not self._initialized:
            await self.initialize()

        if message is None:
            message = f"[MiLyfe] Auto-snapshot at {datetime.utcnow().isoformat()}"

        try:
            # Stage all changes
            await self._run_git("add", "-A")

            # Check if there are changes to commit
            status_output = await self._run_git("status", "--porcelain")
            if not status_output.strip():
                logger.debug("No changes to snapshot")
                return None

            # Commit
            await self._run_git("commit", "-m", message)

            # Get the commit hash
            commit_hash = await self._run_git("rev-parse", "HEAD")
            commit_hash = commit_hash.strip()

            logger.info("Git snapshot created: %s", commit_hash[:8])
            return commit_hash

        except Exception as e:
            logger.error("Git snapshot failed: %s", e)
            return None

    async def get_history(self, limit: int = 20) -> List[Dict[str, str]]:
        """
        Get recent git commit history.

        Args:
            limit: Maximum number of commits to return.

        Returns:
            List of commit dicts with 'hash', 'message', 'date', 'author'.
        """
        if not self._initialized:
            await self.initialize()

        try:
            output = await self._run_git(
                "log",
                f"--max-count={limit}",
                "--format=%H|%s|%ai|%an",
            )

            commits: List[Dict[str, str]] = []
            for line in output.strip().split("\n"):
                if not line.strip():
                    continue
                parts = line.split("|", 3)
                if len(parts) >= 4:
                    commits.append({
                        "hash": parts[0],
                        "message": parts[1],
                        "date": parts[2],
                        "author": parts[3],
                    })
                elif len(parts) == 3:
                    commits.append({
                        "hash": parts[0],
                        "message": parts[1],
                        "date": parts[2],
                        "author": "unknown",
                    })

            return commits

        except Exception as e:
            logger.error("Failed to get git history: %s", e)
            return []

    async def get_diff(self) -> str:
        """Get the current uncommitted diff."""
        if not self._initialized:
            await self.initialize()

        try:
            return await self._run_git("diff")
        except Exception as e:
            logger.error("Failed to get diff: %s", e)
            return ""

    async def _run_git(self, *args: str) -> str:
        """
        Run a git command asynchronously.

        Args:
            *args: Git command arguments.

        Returns:
            stdout output as string.

        Raises:
            RuntimeError: If git command fails.
        """
        cmd = ["git"] + list(args)
        cwd = str(self._workspace) if self._workspace else "."

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=cwd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()

            if proc.returncode != 0:
                error_msg = stderr.decode().strip()
                # Non-fatal for some git operations
                if "nothing to commit" in error_msg or "nothing added" in error_msg:
                    return ""
                raise RuntimeError(f"Git command failed: {' '.join(cmd)}: {error_msg}")

            return stdout.decode()

        except FileNotFoundError:
            raise RuntimeError("Git is not installed or not in PATH")


workspace_git = WorkspaceGit()
