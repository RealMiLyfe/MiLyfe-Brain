"""
MiLyfe Brain - File Lock Service

Provides cooperative file locking to prevent concurrent agent
access to the same file. Uses an in-memory lock registry.
"""
from __future__ import annotations

import logging
import time
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)

# Lock registry: path -> (agent_id, acquired_at timestamp)
_locks: Dict[str, Tuple[str, float]] = {}

# Lock timeout in seconds (auto-release stale locks)
_LOCK_TIMEOUT: float = 300.0  # 5 minutes


def acquire_lock(path: str, agent_id: str) -> bool:
    """
    Acquire a cooperative lock on a file path.

    Args:
        path: File path to lock.
        agent_id: ID of the agent requesting the lock.

    Returns:
        True if lock acquired, False if already locked by another agent.
    """
    _cleanup_stale_locks()

    normalized = _normalize_path(path)
    existing = _locks.get(normalized)

    if existing is not None:
        owner, acquired_at = existing
        if owner == agent_id:
            # Already own the lock — refresh it
            _locks[normalized] = (agent_id, time.time())
            return True
        else:
            logger.debug(
                "Lock denied: path '%s' held by agent '%s' (requested by '%s')",
                path, owner, agent_id,
            )
            return False

    _locks[normalized] = (agent_id, time.time())
    logger.debug("Lock acquired: path '%s' by agent '%s'", path, agent_id)
    return True


def release_lock(path: str, agent_id: str) -> bool:
    """
    Release a cooperative lock on a file path.

    Args:
        path: File path to unlock.
        agent_id: ID of the agent releasing the lock.

    Returns:
        True if released, False if not owned by this agent.
    """
    normalized = _normalize_path(path)
    existing = _locks.get(normalized)

    if existing is None:
        return True  # Already unlocked

    owner, _ = existing
    if owner != agent_id:
        logger.warning(
            "Cannot release lock: path '%s' owned by '%s', not '%s'",
            path, owner, agent_id,
        )
        return False

    del _locks[normalized]
    logger.debug("Lock released: path '%s' by agent '%s'", path, agent_id)
    return True


def is_locked(path: str) -> bool:
    """Check if a file path is currently locked."""
    _cleanup_stale_locks()
    normalized = _normalize_path(path)
    return normalized in _locks


def get_lock_owner(path: str) -> Optional[str]:
    """Get the agent ID that holds the lock on a path."""
    _cleanup_stale_locks()
    normalized = _normalize_path(path)
    existing = _locks.get(normalized)
    return existing[0] if existing else None


def release_all_agent_locks(agent_id: str) -> int:
    """
    Release all locks held by a specific agent.

    Args:
        agent_id: Agent whose locks should be released.

    Returns:
        Number of locks released.
    """
    to_remove = [
        path for path, (owner, _) in _locks.items()
        if owner == agent_id
    ]
    for path in to_remove:
        del _locks[path]

    if to_remove:
        logger.debug("Released %d locks for agent '%s'", len(to_remove), agent_id)

    return len(to_remove)


def get_all_locks() -> Dict[str, Dict[str, str]]:
    """Get all current locks (for debugging/admin)."""
    _cleanup_stale_locks()
    return {
        path: {"agent_id": owner, "acquired_at": str(acquired_at)}
        for path, (owner, acquired_at) in _locks.items()
    }


def _cleanup_stale_locks() -> None:
    """Remove locks that have exceeded the timeout."""
    now = time.time()
    stale = [
        path for path, (_, acquired_at) in _locks.items()
        if (now - acquired_at) > _LOCK_TIMEOUT
    ]
    for path in stale:
        owner = _locks[path][0]
        del _locks[path]
        logger.info("Stale lock expired: path '%s' (was held by '%s')", path, owner)


def _normalize_path(path: str) -> str:
    """Normalize a file path for consistent lookup."""
    import os
    return os.path.normpath(os.path.abspath(path))
