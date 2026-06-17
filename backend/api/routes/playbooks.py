"""MiLyfe Brain — Playbook CRUD + Execution Routes."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

import orjson
import structlog
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from memory.database import PlaybookRow, PlaybookStepRow, async_session_factory, get_session
from models.schemas import (
    Playbook,
    PlaybookCreate,
    PlaybookStatus,
    PlaybookStep,
    TaskGraph,
    GraphNode,
    GraphEdge,
    GraphPosition,
    TaskStatus,
)

logger = structlog.get_logger()
router = APIRouter()


def _row_to_playbook(row: PlaybookRow, steps: Optional[list] = None) -> Playbook:
    """Convert DB row to Playbook schema."""
    playbook_steps = []
    if steps:
        for s in steps:
            playbook_steps.append(
                PlaybookStep(
                    id=s.id,
                    description=s.description,
                    agent_role=s.agent_role,
                    depends_on=orjson.loads(s.depends_on) if s.depends_on else [],
                    complexity=s.complexity or "medium",
                    tools_needed=orjson.loads(s.tools_needed) if s.tools_needed else [],
                    status=s.status or "pending",
                    result=s.result,
                    started_at=s.started_at,
                    completed_at=s.completed_at,
                    error=s.error,
                )
            )
    return Playbook(
        id=row.id,
        title=row.title,
        description=row.description,
        raw_text=row.raw_text,
        steps=playbook_steps,
        status=row.status or "queued",
        created_at=row.created_at,
        started_at=row.started_at,
        completed_at=row.completed_at,
        error=row.error,
        model_override=row.model_override,
        tags=orjson.loads(row.tags) if row.tags else [],
        total_tokens=row.total_tokens or 0,
    )


@router.post("/", response_model=Playbook)
async def create_playbook(data: PlaybookCreate, background_tasks: BackgroundTasks):
    """Create and optionally execute a playbook."""
    playbook_id = str(uuid.uuid4())

    async with async_session_factory() as session:
        row = PlaybookRow(
            id=playbook_id,
            title=data.title,
            description=data.description,
            raw_text=data.raw_text,
            status="queued",
            created_at=datetime.utcnow(),
            model_override=data.model_override,
            tags=orjson.dumps(data.tags).decode() if data.tags else None,
        )
        session.add(row)

        # Add pre-defined steps if provided
        if data.steps:
            for idx, step in enumerate(data.steps):
                step_row = PlaybookStepRow(
                    id=step.id or str(uuid.uuid4()),
                    playbook_id=playbook_id,
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

    # Auto-execute if requested
    if data.auto_execute:
        background_tasks.add_task(_execute_playbook, playbook_id)

    # Fetch the complete playbook
    async with async_session_factory() as session:
        row = await session.get(PlaybookRow, playbook_id)
        steps_result = await session.execute(
            select(PlaybookStepRow).where(PlaybookStepRow.playbook_id == playbook_id).order_by(PlaybookStepRow.order_index)
        )
        steps = steps_result.scalars().all()
        return _row_to_playbook(row, steps)


@router.get("/", response_model=List[Playbook])
async def list_playbooks(limit: int = 50, offset: int = 0):
    """List all playbooks."""
    async with async_session_factory() as session:
        result = await session.execute(
            select(PlaybookRow).order_by(PlaybookRow.created_at.desc()).offset(offset).limit(limit)
        )
        rows = result.scalars().all()
        playbooks = []
        for row in rows:
            steps_result = await session.execute(
                select(PlaybookStepRow).where(PlaybookStepRow.playbook_id == row.id).order_by(PlaybookStepRow.order_index)
            )
            steps = steps_result.scalars().all()
            playbooks.append(_row_to_playbook(row, steps))
        return playbooks


@router.get("/{playbook_id}", response_model=Playbook)
async def get_playbook(playbook_id: str):
    """Get playbook details."""
    async with async_session_factory() as session:
        row = await session.get(PlaybookRow, playbook_id)
        if not row:
            raise HTTPException(status_code=404, detail="Playbook not found")
        steps_result = await session.execute(
            select(PlaybookStepRow).where(PlaybookStepRow.playbook_id == playbook_id).order_by(PlaybookStepRow.order_index)
        )
        steps = steps_result.scalars().all()
        return _row_to_playbook(row, steps)


@router.get("/{playbook_id}/status")
async def get_playbook_status(playbook_id: str):
    """Real-time execution status."""
    async with async_session_factory() as session:
        row = await session.get(PlaybookRow, playbook_id)
        if not row:
            raise HTTPException(status_code=404, detail="Playbook not found")
        steps_result = await session.execute(
            select(PlaybookStepRow).where(PlaybookStepRow.playbook_id == playbook_id)
        )
        steps = steps_result.scalars().all()
        total = len(steps)
        completed = sum(1 for s in steps if s.status == "completed")
        failed = sum(1 for s in steps if s.status == "failed")
        running = sum(1 for s in steps if s.status == "running")

        return {
            "playbook_id": playbook_id,
            "status": row.status,
            "progress": completed / total if total > 0 else 0,
            "total_steps": total,
            "completed_steps": completed,
            "failed_steps": failed,
            "running_steps": running,
            "error": row.error,
        }


@router.get("/{playbook_id}/graph", response_model=TaskGraph)
async def get_playbook_graph(playbook_id: str):
    """Task graph for visualization."""
    async with async_session_factory() as session:
        row = await session.get(PlaybookRow, playbook_id)
        if not row:
            raise HTTPException(status_code=404, detail="Playbook not found")
        steps_result = await session.execute(
            select(PlaybookStepRow).where(PlaybookStepRow.playbook_id == playbook_id).order_by(PlaybookStepRow.order_index)
        )
        steps = steps_result.scalars().all()

        nodes = []
        edges = []
        for idx, step in enumerate(steps):
            nodes.append(GraphNode(
                id=step.id,
                label=step.description[:50],
                type=step.agent_role or "unknown",
                status=step.status or "pending",
                position=GraphPosition(x=idx * 200, y=(idx % 3) * 100),
                data={"agent_role": step.agent_role, "complexity": step.complexity},
            ))
            deps = orjson.loads(step.depends_on) if step.depends_on else []
            for dep in deps:
                edges.append(GraphEdge(
                    id=f"{dep}->{step.id}",
                    source=dep,
                    target=step.id,
                    animated=step.status == "running",
                ))

        return TaskGraph(nodes=nodes, edges=edges)


@router.post("/{playbook_id}/rerun", response_model=Playbook)
async def rerun_playbook(playbook_id: str, background_tasks: BackgroundTasks):
    """Re-execute a playbook."""
    async with async_session_factory() as session:
        row = await session.get(PlaybookRow, playbook_id)
        if not row:
            raise HTTPException(status_code=404, detail="Playbook not found")

        # Reset status
        row.status = "queued"
        row.error = None
        row.started_at = None
        row.completed_at = None

        # Reset all steps
        steps_result = await session.execute(
            select(PlaybookStepRow).where(PlaybookStepRow.playbook_id == playbook_id)
        )
        for step in steps_result.scalars().all():
            step.status = "pending"
            step.result = None
            step.error = None
            step.started_at = None
            step.completed_at = None

        await session.commit()

    background_tasks.add_task(_execute_playbook, playbook_id)

    return await get_playbook(playbook_id)


@router.delete("/{playbook_id}")
async def delete_playbook(playbook_id: str):
    """Delete a playbook and its steps."""
    async with async_session_factory() as session:
        row = await session.get(PlaybookRow, playbook_id)
        if not row:
            raise HTTPException(status_code=404, detail="Playbook not found")

        # Delete steps
        steps_result = await session.execute(
            select(PlaybookStepRow).where(PlaybookStepRow.playbook_id == playbook_id)
        )
        for step in steps_result.scalars().all():
            await session.delete(step)

        await session.delete(row)
        await session.commit()

    return {"detail": "Playbook deleted", "id": playbook_id}


async def _execute_playbook(playbook_id: str):
    """Background task to execute a playbook via the orchestrator."""
    try:
        from graphs.orchestrator import execute_playbook
        await execute_playbook(playbook_id)
    except Exception as e:
        logger.error("playbook_execution_failed", playbook_id=playbook_id, error=str(e))
        async with async_session_factory() as session:
            row = await session.get(PlaybookRow, playbook_id)
            if row:
                row.status = "failed"
                row.error = str(e)
                row.completed_at = datetime.utcnow()
                await session.commit()
