"""Environment Snapshot — Capture project environment at session start."""

import os
import platform
import subprocess
from pathlib import Path
from typing import Optional

import structlog

from config import settings

logger = structlog.get_logger()


class EnvSnapshot:
    """Capture and provide environment information."""

    def __init__(self):
        self._snapshot: Optional[dict] = None

    async def capture(self) -> dict:
        """Capture current environment state."""
        workspace = Path(settings.workspace_dir)

        self._snapshot = {
            "platform": platform.system(),
            "python_version": platform.python_version(),
            "workspace": str(workspace),
            "workspace_exists": workspace.exists(),
            "git_status": await self._git_status(workspace),
            "directory_tree": self._get_tree(workspace, max_depth=2),
            "recent_files": self._get_recent_files(workspace, limit=10),
        }
        return self._snapshot

    def get_prompt_context(self) -> str:
        """Get formatted environment context for agent prompts."""
        if not self._snapshot:
            return ""

        parts = ["## Environment"]
        parts.append(f"- Platform: {self._snapshot.get('platform', 'unknown')}")
        parts.append(f"- Python: {self._snapshot.get('python_version', 'unknown')}")
        parts.append(f"- Workspace: {self._snapshot.get('workspace', 'unknown')}")

        git = self._snapshot.get("git_status")
        if git:
            parts.append(f"- Git: {git}")

        tree = self._snapshot.get("directory_tree", "")
        if tree:
            parts.append(f"\nDirectory structure:\n{tree}")

        return "\n".join(parts)

    async def _git_status(self, workspace: Path) -> str:
        """Get git status summary."""
        if not (workspace / ".git").exists():
            return "Not a git repository"
        try:
            result = subprocess.run(
                ["git", "status", "--short"],
                cwd=str(workspace), capture_output=True, text=True, timeout=5
            )
            lines = result.stdout.strip().split("\n")
            return f"{len(lines)} changed files" if lines[0] else "Clean"
        except Exception:
            return "Unknown"

    def _get_tree(self, path: Path, max_depth: int = 2, prefix: str = "") -> str:
        """Get directory tree string."""
        if not path.exists():
            return "(workspace not initialized)"

        skip = {".git", "node_modules", "__pycache__", ".next", "venv"}
        lines = []
        try:
            items = sorted(path.iterdir(), key=lambda x: (not x.is_dir(), x.name))
            for i, item in enumerate(items[:20]):
                if item.name in skip:
                    continue
                connector = "└── " if i == len(items) - 1 else "├── "
                lines.append(f"{prefix}{connector}{item.name}")
                if item.is_dir() and max_depth > 0:
                    extension = "    " if i == len(items) - 1 else "│   "
                    sub = self._get_tree(item, max_depth - 1, prefix + extension)
                    if sub:
                        lines.append(sub)
        except PermissionError:
            pass

        return "\n".join(lines)

    def _get_recent_files(self, path: Path, limit: int = 10) -> list[str]:
        """Get recently modified files."""
        if not path.exists():
            return []

        skip = {".git", "node_modules", "__pycache__"}
        files = []
        for f in path.rglob("*"):
            if f.is_file():
                if any(p in f.parts for p in skip):
                    continue
                files.append((f, f.stat().st_mtime))

        files.sort(key=lambda x: x[1], reverse=True)
        return [str(f[0].relative_to(path)) for f in files[:limit]]


# Global instance
env_snapshot = EnvSnapshot()
