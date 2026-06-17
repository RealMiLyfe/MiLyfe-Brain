"""MiLyfe Brain — Git-Based Workspace Snapshots."""

from __future__ import annotations

import structlog

from services.workspace_git import workspace_git

logger = structlog.get_logger()


async def pre_execution_snapshot(playbook_id: str):
    """Create a snapshot before playbook execution."""
    await workspace_git.snapshot(f"pre-exec: {playbook_id[:8]}")


async def post_execution_snapshot(playbook_id: str, status: str):
    """Create a snapshot after playbook execution."""
    await workspace_git.snapshot(f"post-exec ({status}): {playbook_id[:8]}")


async def rollback_to_last():
    """Rollback workspace to last snapshot."""
    import asyncio
    from config import settings
    from pathlib import Path

    workspace = Path(settings.workspace_dir)
    if not (workspace / ".git").exists():
        return "No git history available"

    proc = await asyncio.create_subprocess_exec(
        "git", "checkout", "--", ".",
        cwd=str(workspace),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    return "Rolled back to last snapshot"
