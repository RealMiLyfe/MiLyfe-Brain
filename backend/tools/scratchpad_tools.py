"""
MiLyfe Brain - Scratchpad Tools

Per-session scratchpads for notes, todos, decisions, and findings.
"""
from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional, TYPE_CHECKING
from uuid import uuid4

from models.schemas import PermissionLevel

if TYPE_CHECKING:
    from tools.registry import ToolRegistry

# Per-session scratchpads: session_id -> list of entries
_scratchpads: Dict[str, List[Dict[str, str]]] = {}

VALID_CATEGORIES = {"todo", "note", "decision", "finding", "blocker"}


def _get_pad(session_id: str) -> List[Dict[str, str]]:
    """Get or create a scratchpad for a session."""
    if session_id not in _scratchpads:
        _scratchpads[session_id] = []
    return _scratchpads[session_id]


def scratchpad_write(
    content: str,
    category: str = "note",
    session_id: str = "default",
) -> str:
    """Write an entry to the scratchpad.

    Args:
        content: Entry content text.
        category: Category - todo, note, decision, finding, blocker.
        session_id: Session identifier.

    Returns:
        Confirmation with entry ID.
    """
    if not content.strip():
        return "Error: Content cannot be empty"

    if category not in VALID_CATEGORIES:
        return f"Error: Invalid category '{category}'. Valid: {', '.join(sorted(VALID_CATEGORIES))}"

    pad = _get_pad(session_id)
    entry_id = str(uuid4())[:8]
    entry = {
        "id": entry_id,
        "content": content.strip(),
        "category": category,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": None,
    }
    pad.append(entry)

    return f"Added [{category}] entry {entry_id}: {content[:60]}{'...' if len(content) > 60 else ''}"


def scratchpad_read(
    category: str = "",
    session_id: str = "default",
) -> str:
    """Read scratchpad entries, optionally filtered by category.

    Args:
        category: Filter by category (empty = all).
        session_id: Session identifier.

    Returns:
        Formatted scratchpad entries.
    """
    pad = _get_pad(session_id)

    if not pad:
        return f"Scratchpad '{session_id}' is empty"

    if category:
        if category not in VALID_CATEGORIES:
            return f"Error: Invalid category '{category}'. Valid: {', '.join(sorted(VALID_CATEGORIES))}"
        entries = [e for e in pad if e["category"] == category]
        if not entries:
            return f"No entries with category '{category}'"
    else:
        entries = pad

    lines = [f"Scratchpad '{session_id}' ({len(entries)} entries):"]
    lines.append("")

    # Group by category
    by_category: Dict[str, List[Dict[str, str]]] = {}
    for entry in entries:
        cat = entry["category"]
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(entry)

    category_icons = {
        "todo": "[TODO]",
        "note": "[NOTE]",
        "decision": "[DECISION]",
        "finding": "[FINDING]",
        "blocker": "[BLOCKER]",
    }

    for cat in sorted(by_category.keys()):
        icon = category_icons.get(cat, f"[{cat.upper()}]")
        lines.append(f"--- {icon} ---")
        for entry in by_category[cat]:
            updated = f" (updated {entry['updated_at']})" if entry.get("updated_at") else ""
            lines.append(f"  [{entry['id']}] {entry['content']}{updated}")
        lines.append("")

    return "\n".join(lines)


def scratchpad_update(
    entry_id: str,
    content: str,
    session_id: str = "default",
) -> str:
    """Update an existing scratchpad entry.

    Args:
        entry_id: Entry ID to update.
        content: New content.
        session_id: Session identifier.

    Returns:
        Confirmation message.
    """
    if not content.strip():
        return "Error: Content cannot be empty"

    pad = _get_pad(session_id)

    for entry in pad:
        if entry["id"] == entry_id:
            old_content = entry["content"]
            entry["content"] = content.strip()
            entry["updated_at"] = datetime.utcnow().isoformat()
            return f"Updated entry {entry_id}: '{old_content[:30]}...' -> '{content[:30]}...'"

    return f"Error: Entry '{entry_id}' not found in session '{session_id}'"


def get_scratchpad_context(session_id: str = "default") -> str:
    """Get scratchpad content formatted for prompt injection.

    Args:
        session_id: Session identifier.

    Returns:
        Formatted scratchpad context for system prompt inclusion.
    """
    pad = _get_pad(session_id)
    if not pad:
        return ""

    lines = ["<scratchpad>"]

    # Blockers first (highest priority)
    blockers = [e for e in pad if e["category"] == "blocker"]
    if blockers:
        lines.append("BLOCKERS:")
        for e in blockers:
            lines.append(f"  - {e['content']}")

    # Todos
    todos = [e for e in pad if e["category"] == "todo"]
    if todos:
        lines.append("TODO:")
        for e in todos:
            lines.append(f"  - {e['content']}")

    # Decisions
    decisions = [e for e in pad if e["category"] == "decision"]
    if decisions:
        lines.append("DECISIONS:")
        for e in decisions:
            lines.append(f"  - {e['content']}")

    # Findings
    findings = [e for e in pad if e["category"] == "finding"]
    if findings:
        lines.append("FINDINGS:")
        for e in findings:
            lines.append(f"  - {e['content']}")

    # Notes (lower priority)
    notes = [e for e in pad if e["category"] == "note"]
    if notes:
        lines.append("NOTES:")
        for e in notes:
            lines.append(f"  - {e['content']}")

    lines.append("</scratchpad>")
    return "\n".join(lines)


def register_scratchpad_tools(registry: ToolRegistry) -> None:
    """Register scratchpad tools with the tool registry."""
    registry.register(
        name="scratchpad_write",
        handler=scratchpad_write,
        category="scratchpad",
        description="Write an entry to the agent scratchpad (todo, note, decision, finding, blocker).",
        parameters={
            "content": {"type": "string", "description": "Entry content", "required": True},
            "category": {"type": "string", "description": "Category: todo, note, decision, finding, blocker", "default": "note"},
            "session_id": {"type": "string", "description": "Session identifier", "default": "default"},
        },
        permission=PermissionLevel.SAFE,
        returns="Confirmation with entry ID",
    )
    registry.register(
        name="scratchpad_read",
        handler=scratchpad_read,
        category="scratchpad",
        description="Read scratchpad entries, optionally filtered by category.",
        parameters={
            "category": {"type": "string", "description": "Filter by category (empty = all)", "default": ""},
            "session_id": {"type": "string", "description": "Session identifier", "default": "default"},
        },
        permission=PermissionLevel.SAFE,
        returns="Formatted scratchpad entries",
    )
    registry.register(
        name="scratchpad_update",
        handler=scratchpad_update,
        category="scratchpad",
        description="Update an existing scratchpad entry by ID.",
        parameters={
            "entry_id": {"type": "string", "description": "Entry ID to update", "required": True},
            "content": {"type": "string", "description": "New content", "required": True},
            "session_id": {"type": "string", "description": "Session identifier", "default": "default"},
        },
        permission=PermissionLevel.SAFE,
        returns="Confirmation message",
    )
