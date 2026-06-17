"""Workspace Git — Git snapshot operations for workspace versioning.

Provides initialization, snapshot creation, and snapshot listing
for the user's workspace directory.
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime
from typing import List

from config import settings

logger = logging.getLogger(__name__)


async def _run_git(args: List[str], cwd: str) -> str:
    """Run a git command and return stdout."""
    proc = await asyncio.create_subprocess_exec(
        "git", *args,
        cwd=cwd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        error_msg = stderr.decode().strip()
        raise RuntimeError(f"git {' '.join(args)} failed: {error_msg}")
    return stdout.decode().strip()


async def init_workspace_git() -> None:
    """Initialize git in the workspace directory if not already initialized."""
    workspace = settings.workspace_dir

    if not os.path.exists(workspace):
        os.makedirs(workspace, exist_ok=True)

    git_dir = os.path.join(workspace, ".git")
    if os.path.exists(git_dir):
        logger.debug("Workspace git already initialized")
        return

    try:
        await _run_git(["init"], cwd=workspace)
        await _run_git(["config", "user.email", "brain@milyfe.local"], cwd=workspace)
        await _run_git(["config", "user.name", "MiLyfe Brain"], cwd=workspace)

        # Create initial commit with .gitignore
        gitignore_path = os.path.join(workspace, ".gitignore")
        if not os.path.exists(gitignore_path):
            with open(gitignore_path, "w") as f:
                f.write("__pycache__/\n.env\nnode_modules/\n.venv/\n")

        await _run_git(["add", "-A"], cwd=workspace)
        await _run_git(["commit", "-m", "Initial workspace snapshot", "--allow-empty"], cwd=workspace)
        logger.info("Workspace git initialized at %s", workspace)

    except Exception as e:
        logger.warning("Failed to initialize workspace git: %s", e)


async def create_snapshot(message: str) -> str:
    """Create a git snapshot (commit) of the current workspace state.

    Args:
        message: Commit message for the snapshot.

    Returns:
        The commit SHA.
    """
    workspace = settings.workspace_dir

    try:
        await _run_git(["add", "-A"], cwd=workspace)
        await _run_git(["commit", "-m", message, "--allow-empty"], cwd=workspace)
        sha = await _run_git(["rev-parse", "HEAD"], cwd=workspace)
        logger.info("Snapshot created: %s (%s)", sha[:8], message)
        return sha
    except Exception as e:
        logger.error("Snapshot creation failed: %s", e)
        raise


async def list_snapshots(limit: int = 20) -> List[dict]:
    """List recent git snapshots (commits).

    Args:
        limit: Maximum number of snapshots to return.

    Returns:
        List of snapshot dicts with sha, message, and timestamp.
    """
    workspace = settings.workspace_dir
    git_dir = os.path.join(workspace, ".git")

    if not os.path.exists(git_dir):
        return []

    try:
        log_output = await _run_git(
            ["log", f"--max-count={limit}", "--format=%H|%s|%aI"],
            cwd=workspace,
        )

        if not log_output:
            return []

        snapshots = []
        for line in log_output.split("\n"):
            parts = line.split("|", 2)
            if len(parts) == 3:
                snapshots.append({
                    "sha": parts[0],
                    "message": parts[1],
                    "timestamp": parts[2],
                })
        return snapshots

    except Exception as e:
        logger.warning("Failed to list snapshots: %s", e)
        return []
