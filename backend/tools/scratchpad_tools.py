"""Scratchpad Tools — Per-session working memory."""

from datetime import datetime
from typing import Optional

# In-memory scratchpad storage
_scratchpads: dict[str, list[dict]] = {}


async def scratchpad_write(content: str, category: str = "note", session_id: str = "default") -> str:
    """Write to the scratchpad (working memory).

    Args:
        content: What to remember
        category: todo, note, decision, finding, blocker
        session_id: Session identifier
    """
    if session_id not in _scratchpads:
        _scratchpads[session_id] = []

    entry = {
        "id": len(_scratchpads[session_id]),
        "content": content,
        "category": category,
        "created_at": datetime.utcnow().isoformat(),
    }
    _scratchpads[session_id].append(entry)
    return f"Scratchpad entry #{entry['id']} saved [{category}]"


async def scratchpad_read(session_id: str = "default", category: Optional[str] = None) -> str:
    """Read scratchpad entries.

    Args:
        session_id: Session identifier
        category: Optional filter by category
    """
    entries = _scratchpads.get(session_id, [])

    if category:
        entries = [e for e in entries if e["category"] == category]

    if not entries:
        return "(scratchpad empty)"

    lines = []
    for e in entries:
        lines.append(f"#{e['id']} [{e['category']}] {e['content']}")
    return "\n".join(lines)


async def scratchpad_update(entry_id: int, content: str, session_id: str = "default") -> str:
    """Update a scratchpad entry.

    Args:
        entry_id: Entry ID to update
        content: New content
        session_id: Session identifier
    """
    entries = _scratchpads.get(session_id, [])

    for entry in entries:
        if entry["id"] == entry_id:
            entry["content"] = content
            entry["updated_at"] = datetime.utcnow().isoformat()
            return f"Scratchpad entry #{entry_id} updated"

    return f"Entry #{entry_id} not found"


def register_scratchpad_tools(registry):
    """Register scratchpad tools with the tool registry."""
    registry.register(
        "scratchpad_write", "Write to working memory", scratchpad_write, permission="free",
        params={"content": "Content to remember", "category": "todo/note/decision/finding/blocker", "session_id": "Session ID"}
    )
    registry.register(
        "scratchpad_read", "Read working memory", scratchpad_read, permission="free",
        params={"session_id": "Session ID", "category": "Optional filter"}
    )
    registry.register(
        "scratchpad_update", "Update scratchpad entry", scratchpad_update, permission="free",
        params={"entry_id": "Entry ID", "content": "New content", "session_id": "Session ID"}
    )
