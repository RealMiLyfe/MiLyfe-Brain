"""Tasks API — List tasks (steps) for a playbook."""

import json
from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from memory.database import PlaybookStepModel, get_db

router = APIRouter()


@router.get("/")
async def list_tasks(
    playbook_id: str = Query(..., description="Playbook ID to list tasks for"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """List all tasks (steps) for a given playbook."""
    result = await db.execute(
        select(PlaybookStepModel)
        .where(PlaybookStepModel.playbook_id == playbook_id)
        .order_by(PlaybookStepModel.order_index)
    )
    rows = result.scalars().all()

    tasks = [
        {
            "id": row.id,
            "playbook_id": row.playbook_id,
            "description": row.description,
            "agent_role": row.agent_role,
            "status": row.status,
            "result": row.result,
            "order_index": row.order_index,
            "depends_on": json.loads(row.depends_on) if row.depends_on else [],
            "complexity": row.complexity,
            "started_at": row.started_at.isoformat() if row.started_at else None,
            "completed_at": row.completed_at.isoformat() if row.completed_at else None,
        }
        for row in rows
    ]

    return {"tasks": tasks, "count": len(tasks)}
