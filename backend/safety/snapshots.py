"""Git-based Workspace Snapshots — Auto backup before/after execution."""

import os
from pathlib import Path
from datetime import datetime
from typing import Optional

import structlog

logger = structlog.get_logger()


class SnapshotManager:
    """Manage git-based workspace snapshots."""

    def __init__(self, workspace_dir: str = None):
        from config import settings
        self.workspace_dir = Path(workspace_dir or settings.workspace_dir)

    async def create_snapshot(self, message: str = None) -> Optional[str]:
        """Create a git snapshot of the workspace.

        Returns commit hash or None if failed.
        """
        from config import settings
        if not settings.auto_git_snapshots:
            return None

        try:
            import git

            if not (self.workspace_dir / ".git").exists():
                repo = git.Repo.init(self.workspace_dir)
            else:
                repo = git.Repo(self.workspace_dir)

            # Stage all changes
            repo.git.add(A=True)

            # Check if there are changes to commit
            if repo.is_dirty() or repo.untracked_files:
                timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
                commit_msg = message or f"Auto-snapshot {timestamp}"
                commit = repo.index.commit(commit_msg)
                logger.info("Snapshot created", commit=str(commit)[:8], message=commit_msg)
                return str(commit)
            else:
                logger.debug("No changes to snapshot")
                return None

        except Exception as e:
            logger.warning("Snapshot creation failed", error=str(e))
            return None

    async def restore_snapshot(self, commit_hash: str) -> bool:
        """Restore workspace to a previous snapshot."""
        try:
            import git
            repo = git.Repo(self.workspace_dir)
            repo.git.checkout(commit_hash, force=True)
            logger.info("Snapshot restored", commit=commit_hash[:8])
            return True
        except Exception as e:
            logger.error("Snapshot restore failed", error=str(e))
            return False

    async def list_snapshots(self, limit: int = 20) -> list[dict]:
        """List recent snapshots."""
        try:
            import git
            repo = git.Repo(self.workspace_dir)
            commits = list(repo.iter_commits(max_count=limit))
            return [
                {
                    "hash": str(c)[:8],
                    "full_hash": str(c),
                    "message": c.message.strip(),
                    "timestamp": c.committed_datetime.isoformat(),
                    "author": str(c.author),
                }
                for c in commits
            ]
        except Exception as e:
            logger.warning("Failed to list snapshots", error=str(e))
            return []


# Global instance
snapshot_manager = SnapshotManager()
