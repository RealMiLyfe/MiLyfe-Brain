"""MiLyfe Brain — Git Workspace Snapshots.

Provides point-in-time snapshots of the workspace using git commits.
Allows agents to create restore points before destructive operations.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Dict, List, Optional

import git

from config import settings

logger = logging.getLogger(__name__)


class SnapshotService:
    """Manages workspace snapshots using git commits.

    Creates tagged commits for easy identification and rollback.
    Works in the configured workspace directory.
    """

    def __init__(self, workspace_path: Optional[str] = None) -> None:
        self._workspace_path = workspace_path or settings.workspace_dir
        self._repo: Optional[git.Repo] = None

    def _get_repo(self) -> git.Repo:
        """Get or initialize the git repository.

        Returns:
            git.Repo instance for the workspace.

        Raises:
            RuntimeError: If the workspace is not a git repository
                and cannot be initialized.
        """
        if self._repo is not None:
            return self._repo

        try:
            self._repo = git.Repo(self._workspace_path)
        except git.InvalidGitRepositoryError:
            # Initialize a new repo if one doesn't exist
            logger.info(f"Initializing git repo at {self._workspace_path}")
            self._repo = git.Repo.init(self._workspace_path)
        except Exception as e:
            raise RuntimeError(f"Failed to access workspace git repo: {e}") from e

        return self._repo

    def create_snapshot(self, message: str) -> str:
        """Create a snapshot (git commit) of the current workspace state.

        Stages all changes and creates a commit with the given message.
        The commit is prefixed with [snapshot] for easy identification.

        Args:
            message: Description of the snapshot (used as commit message).

        Returns:
            The commit hash (SHA) of the created snapshot.

        Raises:
            RuntimeError: If the snapshot cannot be created.
        """
        try:
            repo = self._get_repo()

            # Stage all changes (including untracked files)
            repo.git.add(A=True)

            # Check if there are changes to commit
            if not repo.is_dirty(untracked_files=True) and not repo.untracked_files:
                # Nothing to commit, return HEAD
                if repo.head.is_valid():
                    return repo.head.commit.hexsha
                # Empty repo — create initial commit
                pass

            # Create the commit
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            full_message = f"[snapshot] {message} ({timestamp})"
            commit = repo.index.commit(full_message)

            logger.info(f"Created snapshot: {commit.hexsha[:8]} — {message}")
            return commit.hexsha

        except Exception as e:
            raise RuntimeError(f"Failed to create snapshot: {e}") from e

    def restore_snapshot(self, commit_hash: str) -> bool:
        """Restore the workspace to a previous snapshot.

        Performs a hard reset to the specified commit. This is destructive
        and will discard all changes since that commit.

        Args:
            commit_hash: The SHA hash of the commit to restore to.

        Returns:
            True if the restore succeeded, False otherwise.
        """
        try:
            repo = self._get_repo()
            repo.git.reset("--hard", commit_hash)
            repo.git.clean("-fd")
            logger.info(f"Restored workspace to snapshot: {commit_hash[:8]}")
            return True
        except git.GitCommandError as e:
            logger.error(f"Failed to restore snapshot {commit_hash[:8]}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error restoring snapshot: {e}")
            return False

    def list_snapshots(self, limit: int = 20) -> List[Dict[str, str]]:
        """List recent snapshots (commits prefixed with [snapshot]).

        Args:
            limit: Maximum number of snapshots to return.

        Returns:
            List of dicts with keys: hash, message, timestamp.
        """
        try:
            repo = self._get_repo()

            if not repo.head.is_valid():
                return []

            snapshots: List[Dict[str, str]] = []
            for commit in repo.iter_commits(max_count=limit * 3):
                if commit.message.startswith("[snapshot]"):
                    snapshots.append({
                        "hash": commit.hexsha,
                        "message": commit.message.replace("[snapshot] ", ""),
                        "timestamp": datetime.fromtimestamp(
                            commit.committed_date
                        ).isoformat(),
                    })
                    if len(snapshots) >= limit:
                        break

            return snapshots

        except Exception as e:
            logger.error(f"Failed to list snapshots: {e}")
            return []


# Singleton instance
snapshot_service = SnapshotService()
