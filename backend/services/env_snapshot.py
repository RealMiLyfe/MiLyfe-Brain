"""MiLyfe Brain — Project Environment Capture."""

from __future__ import annotations

import asyncio
import os
from datetime import datetime
from pathlib import Path
from typing import Dict

import structlog

from config import settings

logger = structlog.get_logger()


class EnvSnapshot:
    """Captures project environment at session start for agent awareness."""

    def __init__(self):
        self._snapshot: Dict = {}
        self._last_refresh: datetime | None = None

    async def capture(self) -> Dict:
        """Capture current environment state."""
        workspace = Path(settings.workspace_dir)

        self._snapshot = {
            "timestamp": datetime.utcnow().isoformat(),
            "workspace": str(workspace),
            "directory_tree": await self._get_tree(workspace, max_depth=2),
            "git_status": await self._get_git_status(workspace),
            "recent_files": self._get_recent_files(workspace),
            "runtime": self._get_runtime_info(),
        }
        self._last_refresh = datetime.utcnow()

        return self._snapshot

    def get_for_prompt(self) -> str:
        """Format snapshot for injection into agent prompts."""
        if not self._snapshot:
            return ""

        parts = ["[Environment Context]"]

        tree = self._snapshot.get("directory_tree", "")
        if tree:
            parts.append(f"Workspace:\n{tree}")

        git = self._snapshot.get("git_status", "")
        if git:
            parts.append(f"Git: {git}")

        recent = self._snapshot.get("recent_files", [])
        if recent:
            parts.append(f"Recent files: {', '.join(recent[:5])}")

        return "\n".join(parts)

    async def _get_tree(self, path: Path, max_depth: int = 2) -> str:
        """Get directory tree (limited depth)."""
        if not path.exists():
            return "(empty workspace)"

        lines = []
        self._tree_recurse(path, lines, "", max_depth, 0)
        return "\n".join(lines[:30])  # Cap at 30 lines

    def _tree_recurse(self, path: Path, lines: list, prefix: str, max_depth: int, depth: int):
        if depth >= max_depth:
            return
        try:
            entries = sorted(path.iterdir(), key=lambda x: (not x.is_dir(), x.name))
            for entry in entries[:15]:  # Max 15 per dir
                if entry.name.startswith("."):
                    continue
                icon = "D" if entry.is_dir() else "F"
                lines.append(f"{prefix}{icon} {entry.name}")
                if entry.is_dir():
                    self._tree_recurse(entry, lines, prefix + "  ", max_depth, depth + 1)
        except PermissionError:
            pass

    async def _get_git_status(self, path: Path) -> str:
        """Get git status summary."""
        git_dir = path / ".git"
        if not git_dir.exists():
            return "not a git repo"

        try:
            proc = await asyncio.create_subprocess_exec(
                "git", "status", "--short",
                cwd=str(path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await proc.communicate()
            status = stdout.decode().strip()
            if not status:
                return "clean"
            lines = status.split("\n")
            return f"{len(lines)} changes"
        except Exception:
            return "unknown"

    def _get_recent_files(self, path: Path, limit: int = 10) -> list:
        """Get recently modified files."""
        if not path.exists():
            return []

        files = []
        for f in path.rglob("*"):
            if f.is_file() and not any(p.startswith(".") for p in f.relative_to(path).parts):
                files.append((f.stat().st_mtime, str(f.relative_to(path))))

        files.sort(key=lambda x: -x[0])
        return [f[1] for f in files[:limit]]

    def _get_runtime_info(self) -> Dict:
        """Get runtime environment info."""
        import sys
        return {
            "python": sys.version.split()[0],
            "platform": sys.platform,
            "pid": os.getpid(),
        }


# Singleton
env_snapshot = EnvSnapshot()
