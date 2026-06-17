"""MiLyfe Brain — Playbook Export/Import Routes."""

from __future__ import annotations

import uuid
from datetime import datetime

import orjson
from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from memory.database import PlaybookRow, PlaybookStepRow, async_session_factory
from models.schemas import Playbook, PlaybookExport, PlaybookStep

router = APIRouter()


@router.post("/export/{playbook_id}")
async def export_playbook(playbook_id: str):
    """Export a playbook as JSON."""
    async with async_session_factory() as session:
        row = await session.get(PlaybookRow, playbook_id)
        if not row:
            raise HTTPException(status_code=404, detail="Playbook not found")

        steps_result = await session.execute(
            select(PlaybookStepRow)
            .where(PlaybookStepRow.playbook_id == playbook_id)
            .order_by(PlaybookStepRow.order_index)
        )
        step_rows = steps_result.scalars().all()

        steps = [
            PlaybookStep(
                id=s.id,
                description=s.description,
                agent_role=s.agent_role,
                depends_on=orjson.loads(s.depends_on) if s.depends_on else [],
                complexity=s.complexity or "medium",
                tools_needed=orjson.loads(s.tools_needed) if s.tools_needed else [],
            )
            for s in step_rows
        ]

        playbook = Playbook(
            id=row.id,
            title=row.title,
            description=row.description,
            raw_text=row.raw_text,
            steps=steps,
            status=row.status,
            created_at=row.created_at,
            tags=orjson.loads(row.tags) if row.tags else [],
        )

        export = PlaybookExport(playbook=playbook, steps=steps)
        return export.model_dump()


@router.post("/import")
async def import_playbook(data: PlaybookExport):
    """Import a playbook from JSON."""
    new_id = str(uuid.uuid4())
    playbook = data.playbook

    async with async_session_factory() as session:
        row = PlaybookRow(
            id=new_id,
            title=playbook.title,
            description=playbook.description,
            raw_text=playbook.raw_text,
            status="queued",
            created_at=datetime.utcnow(),
            tags=orjson.dumps(playbook.tags).decode() if playbook.tags else None,
        )
        session.add(row)

        for idx, step in enumerate(data.steps):
            step_row = PlaybookStepRow(
                id=str(uuid.uuid4()),
                playbook_id=new_id,
                description=step.description,
                agent_role=step.agent_role.value if step.agent_role else None,
                status="pending",
                depends_on=orjson.dumps(step.depends_on).decode() if step.depends_on else None,
                complexity=step.complexity.value if step.complexity else "medium",
                tools_needed=orjson.dumps(step.tools_needed).decode() if step.tools_needed else None,
                order_index=idx,
            )
            session.add(step_row)

        await session.commit()

    return {"detail": "Playbook imported", "id": new_id}
