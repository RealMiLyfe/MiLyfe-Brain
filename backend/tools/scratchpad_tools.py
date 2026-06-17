"""Scratchpad (working memory) tools for MiLyfe Brain.

Provides in-memory key-value storage for agent working notes.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


# In-memory scratchpad storage: {session_id: {key: entry_dict}}
_scratchpads: Dict[str, Dict[str, Dict[str, Any]]] = {}

DEFAULT_SESSION = "default"


def _get_pad(session_id: str = DEFAULT_SESSION) -> Dict[str, Dict[str, Any]]:
    """Get or create a scratchpad for the session."""
    if session_id not in _scratchpads:
        _scratchpads[session_id] = {}
    return _scratchpads[session_id]


async def scratchpad_write(
    key: str,
    value: str,
    category: str = "note",
) -> str:
    """Write a value to the agent scratchpad.

    Args:
        key: Key to store the value under.
        value: Value to store.
        category: Category tag (e.g. 'note', 'plan', 'observation').

    Returns:
        Confirmation message.
    """
    pad = _get_pad()

    if key in pad:
        return (
            f"[ERROR] Key '{key}' already exists. "
            "Use scratchpad_update to modify it."
        )

    pad[key] = {
        "value": value,
        "category": category,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    logger.info("scratchpad_write: key=%s category=%s", key, category)
    return f"Stored '{key}' ({category}) — {len(value)} chars"


async def scratchpad_read(key: Optional[str] = None) -> str:
    """Read from the agent scratchpad.

    Args:
        key: Specific key to read. If None, returns all entries.

    Returns:
        The value(s) from the scratchpad.
    """
    pad = _get_pad()

    if key is not None:
        entry = pad.get(key)
        if entry is None:
            return f"[ERROR] Key '{key}' not found in scratchpad."
        return (
            f"Key: {key}\n"
            f"Category: {entry['category']}\n"
            f"Created: {entry['created_at']}\n"
            f"Updated: {entry['updated_at']}\n"
            f"{'─' * 40}\n"
            f"{entry['value']}"
        )

    # Return all entries
    if not pad:
        return "Scratchpad is empty."

    lines = [f"Scratchpad ({len(pad)} entries):"]
    lines.append("─" * 40)
    for k, entry in sorted(pad.items()):
        preview = entry["value"][:80]
        if len(entry["value"]) > 80:
            preview += "..."
        lines.append(
            f"  [{entry['category']}] {k}: {preview}"
        )
    return "\n".join(lines)


async def scratchpad_update(key: str, value: str) -> str:
    """Update an existing scratchpad entry.

    Args:
        key: Key to update.
        value: New value to set.

    Returns:
        Confirmation message.
    """
    pad = _get_pad()

    if key not in pad:
        return f"[ERROR] Key '{key}' not found. Use scratchpad_write to create it."

    pad[key]["value"] = value
    pad[key]["updated_at"] = datetime.now(timezone.utc).isoformat()

    logger.info("scratchpad_update: key=%s", key)
    return f"Updated '{key}' — {len(value)} chars"
