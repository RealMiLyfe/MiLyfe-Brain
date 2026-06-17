"""
MiLyfe Brain - Export/Import Route

Playbook export as JSON and import from JSON.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Dict
from uuid import uuid4

from fastapi import APIRouter, HTTPException, UploadFile, File
from sqlalchemy import select

from memory.database import (
    PlaybookRow,
    PlaybookStepRow,
    async_session_factory,
)
from models.schemas import (
    Playbook,
    PlaybookExport,
    PlaybookStatus,
    PlaybookStep,
    TaskStatus,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/export/{playbook_id}", response_model=PlaybookExport)
async def export_playbook(playbook_id: str) -> PlaybookExport:
    """Export a playbook as shareable JSON."""
    if async_session_factory is None:
        raise HTTPException(status_code=503, detail="Database not available")

    async with async_session_factory() as session:
        result = await session.execute(
            select(PlaybookRow).where(PlaybookRow.id == playbook_id)
        )
        row = result.scalar_one_or_none()
        if row is None:
            raise HTTPException(status_code=404, detail="Playbook not found")

        steps_result = await session.execute(
            select(PlaybookStepRow)
            .where(PlaybookStepRow.playbook_id == playbook_id)
            .order_by(PlaybookStepRow.order_num)
        )
        step_rows = steps_result.scalars().all()

    steps = [
        PlaybookStep(
            id=s.id,
            title=s.title,
            description=s.description or "",
            agent_role=s.agent_role,
            status=s.status,
            order=s.order_num,
            dependencies=json.loads(s.dependencies) if s.dependencies else [],
            output=s.output,
            error=s.error,
        )
        for s in step_rows
    ]

    playbook = Playbook(
        id=row.id,
        title=row.title,
        goal=row.goal,
        context=row.context,
        status=PlaybookStatus(row.status) if row.status in [s.value for s in PlaybookStatus] else PlaybookStatus.DRAFT,
        priority=row.priority,
        tags=json.loads(row.tags) if row.tags else [],
        steps=steps,
        created_at=row.created_at,
        updated_at=row.updated_at,
        completed_at=row.completed_at,
    )

    return PlaybookExport(
        version="1.0",
        playbook=playbook,
        metadata={"exported_by": "milyfe-brain", "source_id": playbook_id},
        exported_at=datetime.utcnow(),
    )


@router.post("/import")
async def import_playbook(file: UploadFile = File(...)) -> Dict[str, Any]:
    """Import a playbook from a JSON file."""
    if async_session_factory is None:
        raise HTTPException(status_code=503, detail="Database not available")

    content = await file.read()
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON file")

    # Parse the export format
    try:
        export = PlaybookExport(**data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid playbook format: {str(e)}")

    # Create new playbook with new ID
    new_id = str(uuid4())
    now = datetime.utcnow()
    pb = export.playbook

    async with async_session_factory() as session:
        row = PlaybookRow(
            id=new_id,
            title=pb.title,
            goal=pb.goal,
            context=pb.context,
            status=PlaybookStatus.DRAFT.value,
            priority=pb.priority,
            tags=json.dumps(pb.tags),
            created_at=now,
            updated_at=now,
        )
        session.add(row)

        # Import steps with new IDs
        id_mapping: Dict[str, str] = {}
        for step in pb.steps:
            new_step_id = str(uuid4())
            id_mapping[step.id] = new_step_id

            step_row = PlaybookStepRow(
                id=new_step_id,
                playbook_id=new_id,
                title=step.title,
                description=step.description,
                agent_role=step.agent_role.value if hasattr(step.agent_role, "value") else str(step.agent_role),
                status=TaskStatus.PENDING.value,
                order_num=step.order,
                dependencies=json.dumps([id_mapping.get(d, d) for d in step.dependencies]),
            )
            session.add(step_row)

        await session.commit()

    return {
        "status": "imported",
        "playbook_id": new_id,
        "title": pb.title,
        "steps": len(pb.steps),
        "original_id": pb.id,
    }
