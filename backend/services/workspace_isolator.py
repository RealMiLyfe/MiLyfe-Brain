"""MiLyfe Brain — Per-Playbook Workspace Isolation."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Optional

import structlog

from config import settings

logger = structlog.get_logger()


class WorkspaceIsolator:
    """Creates isolated workspace directories per playbook."""

    def __init__(self):
        self._base = Path(settings.workspace_dir)

    async def create_isolated(self, playbook_id: str) -> Path:
        """Create an isolated workspace for a playbook."""
        isolated_dir = self._base / ".isolated" / playbook_id[:12]
        isolated_dir.mkdir(parents=True, exist_ok=True)
        logger.debug("workspace_isolated", playbook_id=playbook_id, path=str(isolated_dir))
        return isolated_dir

    async def merge_back(self, playbook_id: str, target: Optional[str] = None):
        """Merge isolated workspace back to main."""
        isolated_dir = self._base / ".isolated" / playbook_id[:12]
        target_dir = Path(target) if target else self._base

        if not isolated_dir.exists():
            return

        for item in isolated_dir.rglob("*"):
            if item.is_file():
                rel = item.relative_to(isolated_dir)
                dest = target_dir / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(item, dest)

        logger.info("workspace_merged", playbook_id=playbook_id)

    async def cleanup(self, playbook_id: str):
        """Remove isolated workspace."""
        isolated_dir = self._base / ".isolated" / playbook_id[:12]
        if isolated_dir.exists():
            shutil.rmtree(isolated_dir)


# Singleton
workspace_isolator = WorkspaceIsolator()
