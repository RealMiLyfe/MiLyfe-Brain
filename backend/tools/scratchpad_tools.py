"""MiLyfe Brain — Scratchpad (Short-Term Working Memory) Tools."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Dict, List

from models.schemas import PermissionLevel, ScratchpadEntry

# In-memory scratchpad (per session)
_scratchpads: Dict[str, List[ScratchpadEntry]] = {}

VALID_CATEGORIES = {"todo", "note", "decision", "finding", "blocker"}


async def scratchpad_write(
    content: str,
    category: str = "note",
    session_id: str = "default",
) -> str:
    """Write an entry to the scratchpad."""
    if category not in VALID_CATEGORIES:
        return f"Invalid category. Use: {', '.join(VALID_CATEGORIES)}"

    entry = ScratchpadEntry(
        id=str(uuid.uuid4())[:8],
        category=category,
        content=content,
        session_id=session_id,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    if session_id not in _scratchpads:
        _scratchpads[session_id] = []
    _scratchpads[session_id].append(entry)

    return f"Added [{category}] {entry.id}: {content[:80]}"


async def scratchpad_read(
    category: str = "",
    session_id: str = "default",
) -> str:
    """Read scratchpad entries (optionally filter by category)."""
    entries = _scratchpads.get(session_id, [])

    if category:
        entries = [e for e in entries if e.category == category]

    if not entries:
        return "(scratchpad empty)" if not category else f"(no {category} entries)"

    lines = []
    for e in entries:
        lines.append(f"[{e.category}] {e.id} ({e.created_at.strftime('%H:%M')}): {e.content}")

    return "\n".join(lines)


async def scratchpad_update(
    entry_id: str,
    content: str,
    session_id: str = "default",
) -> str:
    """Update an existing scratchpad entry."""
    entries = _scratchpads.get(session_id, [])

    for entry in entries:
        if entry.id == entry_id:
            entry.content = content
            entry.updated_at = datetime.utcnow()
            return f"Updated {entry_id}: {content[:80]}"

    return f"Entry not found: {entry_id}"


def get_scratchpad_context(session_id: str = "default") -> str:
    """Get scratchpad contents for context injection (survives compaction)."""
    entries = _scratchpads.get(session_id, [])
    if not entries:
        return ""

    lines = ["\n--- Working Memory (Scratchpad) ---"]
    for e in entries:
        lines.append(f"[{e.category}] {e.content}")
    return "\n".join(lines)


def register_scratchpad_tools(registry):
    """Register scratchpad tools."""
    registry.register(
        name="scratchpad_write",
        handler=scratchpad_write,
        category="Memory",
        description="Write to working memory (survives context compaction)",
        parameters={
            "content": "str",
            "category": "str (todo|note|decision|finding|blocker)",
            "session_id": "str",
        },
        permission=PermissionLevel.FREE,
    )
    registry.register(
        name="scratchpad_read",
        handler=scratchpad_read,
        category="Memory",
        description="Read scratchpad entries",
        parameters={"category": "str (optional filter)", "session_id": "str"},
        permission=PermissionLevel.FREE,
    )
    registry.register(
        name="scratchpad_update",
        handler=scratchpad_update,
        category="Memory",
        description="Update a scratchpad entry",
        parameters={"entry_id": "str", "content": "str", "session_id": "str"},
        permission=PermissionLevel.FREE,
    )
