"""
MiLyfe Brain - State Checkpointer

Simple in-memory state checkpointing with branching support.
Allows saving, restoring, and forking conversation/agent state.
"""
from __future__ import annotations

import copy
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)


class Checkpointer:
    """In-memory state checkpointing with branching."""

    def __init__(self) -> None:
        self._checkpoints: Dict[str, Dict[str, Any]] = {}
        self._branches: Dict[str, List[str]] = {"main": []}

    def checkpoint(
        self,
        messages: List[Dict[str, Any]],
        metadata: Optional[Dict[str, Any]] = None,
        branch: str = "main",
    ) -> str:
        """
        Save a checkpoint of the current state.

        Args:
            messages: List of message dicts to checkpoint.
            metadata: Optional metadata to store with checkpoint.
            branch: Branch name to store checkpoint under.

        Returns:
            Checkpoint ID string.
        """
        checkpoint_id = str(uuid4())

        self._checkpoints[checkpoint_id] = {
            "id": checkpoint_id,
            "messages": copy.deepcopy(messages),
            "metadata": metadata or {},
            "branch": branch,
            "created_at": datetime.utcnow().isoformat(),
        }

        if branch not in self._branches:
            self._branches[branch] = []
        self._branches[branch].append(checkpoint_id)

        logger.debug(
            "Checkpoint %s created on branch %s (%d messages)",
            checkpoint_id, branch, len(messages),
        )

        return checkpoint_id

    def restore(self, checkpoint_id: str) -> Dict[str, Any]:
        """
        Restore state from a checkpoint.

        Args:
            checkpoint_id: ID of checkpoint to restore.

        Returns:
            Dict with messages, metadata, branch, and created_at.

        Raises:
            KeyError: If checkpoint not found.
        """
        if checkpoint_id not in self._checkpoints:
            raise KeyError(f"Checkpoint {checkpoint_id} not found")

        data = self._checkpoints[checkpoint_id]
        return {
            "id": data["id"],
            "messages": copy.deepcopy(data["messages"]),
            "metadata": copy.deepcopy(data["metadata"]),
            "branch": data["branch"],
            "created_at": data["created_at"],
        }

    def fork(self, checkpoint_id: str, new_branch: str) -> str:
        """
        Fork from an existing checkpoint into a new branch.

        Args:
            checkpoint_id: Source checkpoint to fork from.
            new_branch: Name for the new branch.

        Returns:
            New checkpoint ID on the forked branch.

        Raises:
            KeyError: If source checkpoint not found.
        """
        if checkpoint_id not in self._checkpoints:
            raise KeyError(f"Checkpoint {checkpoint_id} not found")

        source = self._checkpoints[checkpoint_id]

        # Create a new checkpoint on the new branch with the same state
        new_id = str(uuid4())
        self._checkpoints[new_id] = {
            "id": new_id,
            "messages": copy.deepcopy(source["messages"]),
            "metadata": {
                **copy.deepcopy(source["metadata"]),
                "forked_from": checkpoint_id,
                "source_branch": source["branch"],
            },
            "branch": new_branch,
            "created_at": datetime.utcnow().isoformat(),
        }

        if new_branch not in self._branches:
            self._branches[new_branch] = []
        self._branches[new_branch].append(new_id)

        logger.debug(
            "Forked checkpoint %s to branch %s (new id: %s)",
            checkpoint_id, new_branch, new_id,
        )

        return new_id

    def list_branches(self) -> Dict[str, int]:
        """
        List all branches with their checkpoint counts.

        Returns:
            Dict mapping branch name to number of checkpoints.
        """
        return {branch: len(ids) for branch, ids in self._branches.items()}

    def get_branch_history(self, branch: str) -> List[Dict[str, Any]]:
        """
        Get checkpoint history for a branch.

        Args:
            branch: Branch name.

        Returns:
            List of checkpoint summaries (id, created_at, message_count).
        """
        if branch not in self._branches:
            return []

        history = []
        for cp_id in self._branches[branch]:
            if cp_id in self._checkpoints:
                cp = self._checkpoints[cp_id]
                history.append({
                    "id": cp["id"],
                    "created_at": cp["created_at"],
                    "message_count": len(cp["messages"]),
                    "metadata": cp["metadata"],
                })

        return history

    def prune(self, branch: str, keep_last: int = 10) -> int:
        """
        Prune old checkpoints from a branch, keeping the most recent ones.

        Args:
            branch: Branch to prune.
            keep_last: Number of recent checkpoints to keep.

        Returns:
            Number of checkpoints pruned.
        """
        if branch not in self._branches:
            return 0

        ids = self._branches[branch]
        if len(ids) <= keep_last:
            return 0

        to_remove = ids[:-keep_last]
        self._branches[branch] = ids[-keep_last:]

        for cp_id in to_remove:
            self._checkpoints.pop(cp_id, None)

        logger.debug("Pruned %d checkpoints from branch %s", len(to_remove), branch)
        return len(to_remove)


# Singleton instance
checkpointer = Checkpointer()
