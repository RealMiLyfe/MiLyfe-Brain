"""MiLyfe Brain — Task Management Routes."""

from __future__ import annotations

from typing import List

import orjson
from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from memory.database import PlaybookStepRow, async_session_factory
from models.schemas import PlaybookStep, TaskStatus

router = APIRouter()


@router.get("/", response_model=List[PlaybookStep])
async def list_tasks(
    playbook_id: str | None = None,
    status: TaskStatus | None = None,
    limit: int = 100,
):
    """List tasks (optionally filtered by playbook or status)."""
    async with async_session_factory() as session:
        query = select(PlaybookStepRow)
        if playbook_id:
            query = query.where(PlaybookStepRow.playbook_id == playbook_id)
        if status:
            query = query.where(PlaybookStepRow.status == status.value)
        query = query.order_by(PlaybookStepRow.order_index).limit(limit)

        result = await session.execute(query)
        rows = result.scalars().all()
        return [
            PlaybookStep(
                id=r.id,
                description=r.description,
                agent_role=r.agent_role,
                depends_on=orjson.loads(r.depends_on) if r.depends_on else [],
                complexity=r.complexity or "medium",
                tools_needed=orjson.loads(r.tools_needed) if r.tools_needed else [],
                status=r.status or "pending",
                result=r.result,
                started_at=r.started_at,
                completed_at=r.completed_at,
                error=r.error,
            )
            for r in rows
        ]


@router.get("/{task_id}", response_model=PlaybookStep)
async def get_task(task_id: str):
    """Get a single task."""
    async with async_session_factory() as session:
        row = await session.get(PlaybookStepRow, task_id)
        if not row:
            raise HTTPException(status_code=404, detail="Task not found")
        return PlaybookStep(
            id=row.id,
            description=row.description,
            agent_role=row.agent_role,
            depends_on=orjson.loads(row.depends_on) if row.depends_on else [],
            complexity=row.complexity or "medium",
            tools_needed=orjson.loads(row.tools_needed) if row.tools_needed else [],
            status=row.status or "pending",
            result=row.result,
            started_at=row.started_at,
            completed_at=row.completed_at,
            error=row.error,
        )


@router.post("/{task_id}/cancel")
async def cancel_task(task_id: str):
    """Cancel a pending or running task."""
    async with async_session_factory() as session:
        row = await session.get(PlaybookStepRow, task_id)
        if not row:
            raise HTTPException(status_code=404, detail="Task not found")
        if row.status in ("completed", "cancelled"):
            raise HTTPException(status_code=400, detail=f"Task already {row.status}")
        row.status = "cancelled"
        await session.commit()
    return {"detail": "Task cancelled", "id": task_id}
