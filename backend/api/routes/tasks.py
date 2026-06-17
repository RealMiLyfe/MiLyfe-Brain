"""
MiLyfe Brain - Tasks Route

Task management: list, get, and cancel tasks within playbooks.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select, update

from memory.database import PlaybookStepRow, async_session_factory
from models.schemas import PlaybookStep, TaskStatus

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/", response_model=List[PlaybookStep])
async def list_tasks(
    playbook_id: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> List[PlaybookStep]:
    """List tasks with optional filters."""
    if async_session_factory is None:
        return []

    async with async_session_factory() as session:
        query = select(PlaybookStepRow).order_by(
            PlaybookStepRow.order_num.asc()
        )
        if playbook_id:
            query = query.where(
                PlaybookStepRow.playbook_id == playbook_id
            )
        if status:
            query = query.where(PlaybookStepRow.status == status)
        query = query.offset(offset).limit(limit)

        result = await session.execute(query)
        rows = result.scalars().all()

    return [
        PlaybookStep(
            id=r.id,
            title=r.title,
            description=r.description or "",
            agent_role=r.agent_role,
            status=r.status,
            order=r.order_num,
            dependencies=json.loads(r.dependencies) if r.dependencies else [],
            output=r.output,
            error=r.error,
            started_at=r.started_at,
            completed_at=r.completed_at,
            retries=r.retries,
        )
        for r in rows
    ]


@router.get("/{task_id}", response_model=PlaybookStep)
async def get_task(task_id: str) -> PlaybookStep:
    """Get a single task by ID."""
    if async_session_factory is None:
        raise HTTPException(status_code=503, detail="Database not available")

    async with async_session_factory() as session:
        result = await session.execute(
            select(PlaybookStepRow).where(PlaybookStepRow.id == task_id)
        )
        row = result.scalar_one_or_none()

    if row is None:
        raise HTTPException(status_code=404, detail="Task not found")

    return PlaybookStep(
        id=row.id,
        title=row.title,
        description=row.description or "",
        agent_role=row.agent_role,
        status=row.status,
        order=row.order_num,
        dependencies=json.loads(row.dependencies) if row.dependencies else [],
        output=row.output,
        error=row.error,
        started_at=row.started_at,
        completed_at=row.completed_at,
        retries=row.retries,
    )


@router.post("/{task_id}/cancel")
async def cancel_task(task_id: str) -> Dict[str, str]:
    """Cancel a running or pending task."""
    if async_session_factory is None:
        raise HTTPException(status_code=503, detail="Database not available")

    async with async_session_factory() as session:
        result = await session.execute(
            select(PlaybookStepRow).where(PlaybookStepRow.id == task_id)
        )
        row = result.scalar_one_or_none()

        if row is None:
            raise HTTPException(status_code=404, detail="Task not found")

        if row.status in (TaskStatus.COMPLETED.value, TaskStatus.CANCELLED.value):
            raise HTTPException(
                status_code=400,
                detail=f"Task already {row.status}",
            )

        await session.execute(
            update(PlaybookStepRow)
            .where(PlaybookStepRow.id == task_id)
            .values(status=TaskStatus.CANCELLED.value)
        )
        await session.commit()

    return {"status": "cancelled", "task_id": task_id}
