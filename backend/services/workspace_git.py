"""Workspace Git — Auto git snapshots for workspace."""

from pathlib import Path
from typing import Optional

import structlog

from config import settings

logger = structlog.get_logger()


class WorkspaceGit:
    """Manage git operations for the workspace."""

    def __init__(self):
        self._initialized: bool = False
        self._workspace = Path(settings.workspace_dir)

    async def init(self) -> None:
        """Initialize git in workspace if not already."""
        if not self._workspace.exists():
            self._workspace.mkdir(parents=True, exist_ok=True)

        git_dir = self._workspace / ".git"
        if not git_dir.exists():
            try:
                import git
                repo = git.Repo.init(self._workspace)
                # Create .gitignore
                gitignore = self._workspace / ".gitignore"
                if not gitignore.exists():
                    gitignore.write_text("node_modules/\n__pycache__/\n.next/\nvenv/\n*.pyc\n")
                repo.git.add(A=True)
                repo.index.commit("Initial workspace snapshot")
                self._initialized = True
            except Exception as e:
                logger.warning("Git init failed", error=str(e))
        else:
            self._initialized = True

    async def snapshot(self, message: str = "Auto-snapshot") -> Optional[str]:
        """Create a git snapshot."""
        if not settings.auto_git_snapshots:
            return None

        try:
            import git
            repo = git.Repo(self._workspace)
            repo.git.add(A=True)
            if repo.is_dirty() or repo.untracked_files:
                commit = repo.index.commit(message)
                return str(commit)[:8]
        except Exception as e:
            logger.debug("Snapshot failed", error=str(e))
        return None


# Global instance
workspace_git = WorkspaceGit()
