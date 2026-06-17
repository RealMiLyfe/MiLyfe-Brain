"""Workspace Isolator — Per-playbook workspace isolation."""

import os
import shutil
from pathlib import Path
from typing import Optional

import structlog

from config import settings

logger = structlog.get_logger()


class WorkspaceIsolator:
    """Isolate playbook execution in separate directories."""

    def __init__(self):
        self._base = Path(settings.workspace_dir)
        self._isolation_dir = self._base / ".isolated"

    async def create_isolated_workspace(self, playbook_id: str) -> str:
        """Create an isolated workspace for a playbook."""
        workspace = self._isolation_dir / playbook_id
        workspace.mkdir(parents=True, exist_ok=True)

        logger.info("Isolated workspace created", playbook_id=playbook_id, path=str(workspace))
        return str(workspace)

    async def merge_to_main(self, playbook_id: str) -> bool:
        """Merge isolated workspace back to main."""
        source = self._isolation_dir / playbook_id
        if not source.exists():
            return False

        try:
            for item in source.rglob("*"):
                if item.is_file():
                    rel = item.relative_to(source)
                    dest = self._base / rel
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(item, dest)

            logger.info("Isolated workspace merged", playbook_id=playbook_id)
            return True
        except Exception as e:
            logger.error("Workspace merge failed", error=str(e))
            return False

    async def cleanup(self, playbook_id: str) -> None:
        """Remove isolated workspace."""
        workspace = self._isolation_dir / playbook_id
        if workspace.exists():
            shutil.rmtree(workspace, ignore_errors=True)


# Global instance
workspace_isolator = WorkspaceIsolator()
