"""MiLyfe Brain — Session Branching (Git-like conversation forking)."""

from __future__ import annotations

from typing import Dict, List, Optional

import structlog

from memory.checkpointer import (
    checkpoint,
    fork,
    get_branch_history,
    list_branches,
    merge_branch,
    restore,
    switch_branch,
)

logger = structlog.get_logger()


class SessionBranching:
    """Provides git-like branching for conversation sessions."""

    async def save_checkpoint(
        self, messages: List[Dict[str, str]], metadata: dict = None
    ) -> str:
        """Save current conversation state."""
        return await checkpoint(messages, metadata)

    async def create_branch(
        self, checkpoint_id: str, branch_name: Optional[str] = None
    ) -> str:
        """Fork from a checkpoint into a new branch."""
        return await fork(checkpoint_id, branch_name)

    async def switch(self, branch_name: str) -> str:
        """Switch to a different branch."""
        return await switch_branch(branch_name)

    async def merge(self, source: str, target: str = "main") -> str:
        """Merge a branch into target."""
        return await merge_branch(source, target)

    async def get_branches(self) -> Dict[str, int]:
        """List all branches."""
        return list_branches()

    async def get_history(self, branch: str = None) -> list:
        """Get checkpoint history."""
        return get_branch_history(branch)

    async def restore_checkpoint(self, checkpoint_id: str) -> dict:
        """Restore from checkpoint."""
        return await restore(checkpoint_id)


# Singleton
session_branching = SessionBranching()
