"""State Checkpointer — Save and restore execution state.

Enables session branching and recovery from failures.
"""

import json
import uuid
from datetime import datetime
from typing import Any, Optional

import structlog

logger = structlog.get_logger()


class Checkpoint:
    """A saved state checkpoint."""

    def __init__(self, checkpoint_id: str, data: dict, metadata: dict):
        self.id = checkpoint_id
        self.data = data
        self.metadata = metadata
        self.created_at = datetime.utcnow().isoformat()


class Checkpointer:
    """State checkpointing for conversation and execution recovery."""

    def __init__(self):
        self._checkpoints: dict[str, Checkpoint] = {}
        self._branches: dict[str, list[str]] = {"main": []}
        self._active_branch: str = "main"

    async def save(self, data: dict, metadata: Optional[dict] = None) -> str:
        """Save a checkpoint and return its ID."""
        checkpoint_id = str(uuid.uuid4())
        checkpoint = Checkpoint(
            checkpoint_id=checkpoint_id,
            data=data,
            metadata=metadata or {},
        )
        self._checkpoints[checkpoint_id] = checkpoint
        self._branches[self._active_branch].append(checkpoint_id)

        logger.debug("Checkpoint saved", id=checkpoint_id, branch=self._active_branch)
        return checkpoint_id

    async def load(self, checkpoint_id: str) -> Optional[dict]:
        """Load a checkpoint by ID."""
        checkpoint = self._checkpoints.get(checkpoint_id)
        if checkpoint:
            return checkpoint.data
        return None

    async def fork(self, checkpoint_id: str, branch_name: Optional[str] = None) -> str:
        """Create a new branch from a checkpoint."""
        if checkpoint_id not in self._checkpoints:
            raise ValueError(f"Checkpoint {checkpoint_id} not found")

        branch_name = branch_name or f"branch_{uuid.uuid4().hex[:8]}"

        # Find all checkpoints up to this point in the source branch
        source_branch = None
        for bname, checkpoints in self._branches.items():
            if checkpoint_id in checkpoints:
                source_branch = bname
                idx = checkpoints.index(checkpoint_id)
                self._branches[branch_name] = checkpoints[:idx + 1]
                break

        if source_branch is None:
            self._branches[branch_name] = [checkpoint_id]

        logger.info("Branch forked", branch=branch_name, from_checkpoint=checkpoint_id)
        return branch_name

    async def switch_branch(self, branch_name: str) -> bool:
        """Switch to a different branch."""
        if branch_name not in self._branches:
            return False
        self._active_branch = branch_name
        logger.info("Switched branch", branch=branch_name)
        return True

    async def merge_branch(self, source: str, target: str) -> bool:
        """Merge source branch into target branch."""
        if source not in self._branches or target not in self._branches:
            return False

        # Simple merge: append source checkpoints not in target
        target_ids = set(self._branches[target])
        for cp_id in self._branches[source]:
            if cp_id not in target_ids:
                self._branches[target].append(cp_id)

        logger.info("Branch merged", source=source, target=target)
        return True

    def get_branch_history(self, branch_name: Optional[str] = None) -> list[dict]:
        """Get checkpoint history for a branch."""
        branch = branch_name or self._active_branch
        checkpoint_ids = self._branches.get(branch, [])

        return [
            {
                "id": cp_id,
                "created_at": self._checkpoints[cp_id].created_at,
                "metadata": self._checkpoints[cp_id].metadata,
            }
            for cp_id in checkpoint_ids
            if cp_id in self._checkpoints
        ]

    def list_branches(self) -> list[dict]:
        """List all branches."""
        return [
            {
                "name": name,
                "checkpoint_count": len(checkpoints),
                "active": name == self._active_branch,
            }
            for name, checkpoints in self._branches.items()
        ]


# Global instance
checkpointer = Checkpointer()
