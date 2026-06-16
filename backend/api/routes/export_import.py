"""Playbook export/import routes."""

from datetime import datetime

from fastapi import APIRouter, HTTPException, UploadFile, File
import json

from models.schemas import PlaybookExport

router = APIRouter()


@router.post("/export/{playbook_id}", response_model=PlaybookExport)
async def export_playbook(playbook_id: str):
    """Export a playbook as JSON."""
    from memory.database import db

    playbook = await db.fetch_one("SELECT * FROM playbooks WHERE id = ?", (playbook_id,))
    if not playbook:
        raise HTTPException(status_code=404, detail="Playbook not found")

    steps = await db.fetch_all(
        "SELECT * FROM playbook_steps WHERE playbook_id = ? ORDER BY rowid", (playbook_id,)
    )

    return PlaybookExport(
        version="1.0",
        playbook=dict(playbook),
        steps=[dict(s) for s in steps],
        exported_at=datetime.utcnow().isoformat(),
    )


@router.post("/import")
async def import_playbook(file: UploadFile = File(...)):
    """Import a playbook from JSON file."""
    import uuid
    from memory.database import db

    content = await file.read()
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON file")

    playbook_data = data.get("playbook", {})
    steps_data = data.get("steps", [])

    # Generate new IDs
    new_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()

    await db.execute(
        """INSERT INTO playbooks (id, title, description, raw_text, status, created_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (
            new_id,
            playbook_data.get("title", "Imported Playbook"),
            playbook_data.get("description", ""),
            playbook_data.get("raw_text"),
            "pending",
            now,
        ),
    )

    for step in steps_data:
        step_id = str(uuid.uuid4())
        await db.execute(
            """INSERT INTO playbook_steps (id, playbook_id, description, agent_role, status)
               VALUES (?, ?, ?, ?, ?)""",
            (step_id, new_id, step.get("description", ""), step.get("agent_role"), "pending"),
        )

    return {"message": "Playbook imported", "playbook_id": new_id}
