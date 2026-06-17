"""MiLyfe Brain — State Checkpointing for conversation/playbook state."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

import orjson
import structlog

logger = structlog.get_logger()

# In-memory checkpoints (could be backed by SQLite for persistence)
_checkpoints: Dict[str, Dict[str, Any]] = {}
_branches: Dict[str, List[str]] = {"main": []}  # branch_name -> [checkpoint_ids]
_active_branch: str = "main"


async def checkpoint(
    messages: List[Dict[str, str]],
    metadata: Optional[Dict[str, Any]] = None,
    branch: Optional[str] = None,
) -> str:
    """Save a state checkpoint. Returns checkpoint_id."""
    cp_id = str(uuid.uuid4())[:12]
    branch = branch or _active_branch

    _checkpoints[cp_id] = {
        "id": cp_id,
        "messages": messages,
        "metadata": metadata or {},
        "branch": branch,
        "timestamp": datetime.utcnow().isoformat(),
    }

    if branch not in _branches:
        _branches[branch] = []
    _branches[branch].append(cp_id)

    logger.debug("checkpoint_saved", id=cp_id, branch=branch, msg_count=len(messages))
    return cp_id


async def restore(checkpoint_id: str) -> Dict[str, Any]:
    """Restore state from a checkpoint."""
    cp = _checkpoints.get(checkpoint_id)
    if not cp:
        raise ValueError(f"Checkpoint not found: {checkpoint_id}")
    return cp


async def fork(checkpoint_id: str, new_branch: str = None) -> str:
    """Fork from a checkpoint into a new branch."""
    cp = _checkpoints.get(checkpoint_id)
    if not cp:
        raise ValueError(f"Checkpoint not found: {checkpoint_id}")

    new_branch = new_branch or f"branch_{uuid.uuid4().hex[:6]}"
    _branches[new_branch] = [checkpoint_id]

    logger.info("branch_forked", from_checkpoint=checkpoint_id, new_branch=new_branch)
    return new_branch


async def switch_branch(branch_name: str) -> str:
    """Switch active branch."""
    global _active_branch
    if branch_name not in _branches:
        raise ValueError(f"Branch not found: {branch_name}")
    _active_branch = branch_name
    return branch_name


async def merge_branch(source: str, target: str = "main") -> str:
    """Merge source branch into target."""
    if source not in _branches:
        raise ValueError(f"Source branch not found: {source}")
    if target not in _branches:
        raise ValueError(f"Target branch not found: {target}")

    # Get latest checkpoint from source
    source_cps = _branches[source]
    if not source_cps:
        return "Nothing to merge"

    latest_cp = _checkpoints.get(source_cps[-1])
    if latest_cp:
        # Create merge checkpoint in target
        merge_id = await checkpoint(
            messages=latest_cp["messages"],
            metadata={"merged_from": source, **latest_cp.get("metadata", {})},
            branch=target,
        )
        logger.info("branch_merged", source=source, target=target, merge_cp=merge_id)
        return merge_id

    return "Merge failed"


def list_branches() -> Dict[str, int]:
    """List all branches with checkpoint counts."""
    return {name: len(cps) for name, cps in _branches.items()}


def get_branch_history(branch: str = None) -> List[Dict[str, Any]]:
    """Get checkpoint history for a branch."""
    branch = branch or _active_branch
    cp_ids = _branches.get(branch, [])
    return [
        {
            "id": cp_id,
            "timestamp": _checkpoints[cp_id]["timestamp"],
            "msg_count": len(_checkpoints[cp_id]["messages"]),
        }
        for cp_id in cp_ids
        if cp_id in _checkpoints
    ]
