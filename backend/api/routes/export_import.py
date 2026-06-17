"""Export/Import API — Playbook serialization."""

import json
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from memory.database import PlaybookModel, PlaybookStepModel, get_db

router = APIRouter()


class ImportRequest(BaseModel):
    """Request body for importing a playbook."""
    data: dict


@router.post("/export/{playbook_id}")
async def export_playbook(
    playbook_id: str, db: AsyncSession = Depends(get_db)
) -> dict:
    """Export a playbook as portable JSON."""
    result = await db.execute(
        select(PlaybookModel).where(PlaybookModel.id == playbook_id)
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Playbook not found")

    steps_data = []
    for step in (row.steps or []):
        steps_data.append({
            "description": step.description,
            "agent_role": step.agent_role,
            "order_index": step.order_index,
            "depends_on": json.loads(step.depends_on) if step.depends_on else [],
            "complexity": step.complexity,
        })

    export_data = {
        "version": "1.0",
        "exported_at": datetime.utcnow().isoformat(),
        "playbook": {
            "title": row.title,
            "description": row.description or "",
            "raw_text": row.raw_text,
            "steps": steps_data,
        },
    }

    return {"export": export_data}


@router.post("/import")
async def import_playbook(
    body: ImportRequest, db: AsyncSession = Depends(get_db)
) -> dict:
    """Import a playbook from exported JSON."""
    data = body.data
    pb_data = data.get("playbook", {})

    if not pb_data.get("title"):
        raise HTTPException(status_code=400, detail="Invalid import data: title required")

    playbook_id = str(uuid.uuid4())

    db_playbook = PlaybookModel(
        id=playbook_id,
        title=pb_data["title"],
        description=pb_data.get("description", ""),
        raw_text=pb_data.get("raw_text"),
        status="pending",
        created_at=datetime.utcnow(),
    )
    db.add(db_playbook)

    for i, step_data in enumerate(pb_data.get("steps", [])):
        step_id = str(uuid.uuid4())
        db_step = PlaybookStepModel(
            id=step_id,
            playbook_id=playbook_id,
            description=step_data.get("description", ""),
            agent_role=step_data.get("agent_role"),
            status="pending",
            order_index=step_data.get("order_index", i),
            depends_on=json.dumps(step_data.get("depends_on", [])),
            complexity=step_data.get("complexity", "medium"),
        )
        db.add(db_step)

    await db.commit()

    return {"message": "Playbook imported", "playbook_id": playbook_id}
