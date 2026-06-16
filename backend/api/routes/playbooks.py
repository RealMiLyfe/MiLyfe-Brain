"""Playbook CRUD + execution routes."""

import uuid
from datetime import datetime

from fastapi import APIRouter, HTTPException

from models.schemas import (
    PlaybookCreate,
    PlaybookResponse,
    PlaybookStatusResponse,
    TaskGraph,
    TaskStatus,
)

router = APIRouter()


@router.post("/", response_model=PlaybookResponse)
async def create_playbook(playbook: PlaybookCreate):
    """Create and optionally execute a playbook."""
    from memory.database import db
    from graphs.orchestrator import orchestrator

    playbook_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()

    # Store in database
    await db.execute(
        """INSERT INTO playbooks (id, title, description, raw_text, status, created_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (playbook_id, playbook.title, playbook.description, playbook.raw_text, "pending", now),
    )

    # Parse and execute if auto_execute
    if playbook.auto_execute:
        from services.queue_manager import queue_manager
        await queue_manager.enqueue(playbook_id)

    return PlaybookResponse(
        id=playbook_id,
        title=playbook.title,
        description=playbook.description,
        raw_text=playbook.raw_text,
        status=TaskStatus.pending,
        created_at=now,
    )


@router.get("/", response_model=list[PlaybookResponse])
async def list_playbooks():
    """List all playbooks."""
    from memory.database import db

    rows = await db.fetch_all("SELECT * FROM playbooks ORDER BY created_at DESC")
    return [
        PlaybookResponse(
            id=row["id"],
            title=row["title"],
            description=row["description"],
            raw_text=row.get("raw_text"),
            status=row["status"],
            created_at=row["created_at"],
            completed_at=row.get("completed_at"),
            error=row.get("error"),
        )
        for row in rows
    ]


@router.get("/{playbook_id}", response_model=PlaybookResponse)
async def get_playbook(playbook_id: str):
    """Get playbook details."""
    from memory.database import db

    row = await db.fetch_one("SELECT * FROM playbooks WHERE id = ?", (playbook_id,))
    if not row:
        raise HTTPException(status_code=404, detail="Playbook not found")

    steps = await db.fetch_all(
        "SELECT * FROM playbook_steps WHERE playbook_id = ? ORDER BY rowid", (playbook_id,)
    )

    return PlaybookResponse(
        id=row["id"],
        title=row["title"],
        description=row["description"],
        raw_text=row.get("raw_text"),
        status=row["status"],
        steps=[dict(s) for s in steps],
        created_at=row["created_at"],
        completed_at=row.get("completed_at"),
        error=row.get("error"),
    )


@router.get("/{playbook_id}/status", response_model=PlaybookStatusResponse)
async def get_playbook_status(playbook_id: str):
    """Get real-time execution status."""
    from memory.database import db

    row = await db.fetch_one("SELECT * FROM playbooks WHERE id = ?", (playbook_id,))
    if not row:
        raise HTTPException(status_code=404, detail="Playbook not found")

    steps = await db.fetch_all(
        "SELECT * FROM playbook_steps WHERE playbook_id = ? ORDER BY rowid", (playbook_id,)
    )

    total = len(steps) if steps else 1
    completed = sum(1 for s in steps if s["status"] == "completed")
    progress = completed / total

    current_step = next((s["description"] for s in steps if s["status"] == "running"), None)

    return PlaybookStatusResponse(
        id=playbook_id,
        status=row["status"],
        progress=progress,
        current_step=current_step,
        steps=[dict(s) for s in steps],
        error=row.get("error"),
    )


@router.get("/{playbook_id}/graph", response_model=TaskGraph)
async def get_playbook_graph(playbook_id: str):
    """Get task graph for visualization."""
    from memory.database import db

    steps = await db.fetch_all(
        "SELECT * FROM playbook_steps WHERE playbook_id = ? ORDER BY rowid", (playbook_id,)
    )

    nodes = []
    edges = []
    for i, step in enumerate(steps):
        nodes.append({
            "id": step["id"],
            "label": step["description"][:50],
            "type": step.get("agent_role", "default"),
            "status": step["status"],
            "position": {"x": 100, "y": i * 120},
            "data": dict(step),
        })

    return TaskGraph(nodes=nodes, edges=edges)


@router.post("/{playbook_id}/rerun")
async def rerun_playbook(playbook_id: str):
    """Re-execute a playbook."""
    from memory.database import db
    from services.queue_manager import queue_manager

    row = await db.fetch_one("SELECT * FROM playbooks WHERE id = ?", (playbook_id,))
    if not row:
        raise HTTPException(status_code=404, detail="Playbook not found")

    # Reset status
    await db.execute(
        "UPDATE playbooks SET status = 'pending', error = NULL, completed_at = NULL WHERE id = ?",
        (playbook_id,),
    )
    await db.execute(
        "UPDATE playbook_steps SET status = 'pending', result = NULL WHERE playbook_id = ?",
        (playbook_id,),
    )

    await queue_manager.enqueue(playbook_id)
    return {"message": "Playbook queued for re-execution", "playbook_id": playbook_id}


@router.delete("/{playbook_id}")
async def delete_playbook(playbook_id: str):
    """Delete a playbook."""
    from memory.database import db

    await db.execute("DELETE FROM playbook_steps WHERE playbook_id = ?", (playbook_id,))
    await db.execute("DELETE FROM playbooks WHERE id = ?", (playbook_id,))
    return {"message": "Playbook deleted", "playbook_id": playbook_id}
