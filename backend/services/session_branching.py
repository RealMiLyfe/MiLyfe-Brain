"""Session Branching — Git-like conversation forking."""

from typing import Optional

import structlog

from memory.checkpointer import checkpointer

logger = structlog.get_logger()


class SessionBranching:
    """Manage conversation branching."""

    async def checkpoint(self, session_id: str, messages: list[dict]) -> str:
        """Save current conversation state."""
        return await checkpointer.save(
            data={"session_id": session_id, "messages": messages},
            metadata={"session_id": session_id, "message_count": len(messages)},
        )

    async def fork(self, checkpoint_id: str, branch_name: Optional[str] = None) -> str:
        """Fork conversation from a checkpoint."""
        return await checkpointer.fork(checkpoint_id, branch_name)

    async def switch(self, branch_name: str) -> bool:
        """Switch to a different conversation branch."""
        return await checkpointer.switch_branch(branch_name)

    async def merge(self, source: str, target: str) -> bool:
        """Merge two conversation branches."""
        return await checkpointer.merge_branch(source, target)

    def list_branches(self) -> list[dict]:
        """List all branches."""
        return checkpointer.list_branches()


# Global instance
session_branching = SessionBranching()
