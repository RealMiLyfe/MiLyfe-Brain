"""
MiLyfe Brain - Playbooks Route

CRUD operations and execution management for playbooks.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import delete, func, select, update

from memory.database import (
    PlaybookRow,
    PlaybookStepRow,
    async_session_factory,
    get_session,
)
from models.schemas import (
    GraphEdge,
    GraphNode,
    GraphPosition,
    Playbook,
    PlaybookCreate,
    PlaybookStatus,
    PlaybookStep,
    TaskGraph,
    TaskStatus,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/", response_model=Playbook)
async def create_playbook(body: PlaybookCreate) -> Playbook:
    """Create a new playbook from a goal description, parse into steps, and queue for execution."""
    if async_session_factory is None:
        raise HTTPException(status_code=503, detail="Database not available")

    playbook_id = str(uuid4())
    now = datetime.utcnow()

    # Parse goal into steps using the playbook parser
    steps: List[PlaybookStep] = []
    try:
        from graphs.playbook_parser import parse_goal_to_steps

        parsed = await parse_goal_to_steps(body.goal, body.context)
        for i, step_data in enumerate(parsed):
            steps.append(PlaybookStep(
                id=str(uuid4()),
                title=step_data.get("title", f"Step {i + 1}"),
                description=step_data.get("description", ""),
                agent_role=step_data.get("agent_role", "orchestrator"),
                order=i,
                dependencies=step_data.get("dependencies", []),
            ))
    except Exception as e:
        logger.warning("Playbook parsing fallback (single step): %s", e)
        steps.append(PlaybookStep(
            id=str(uuid4()),
            title=body.title,
            description=body.goal,
            order=0,
        ))

    # Persist to database
    async with async_session_factory() as session:
        row = PlaybookRow(
            id=playbook_id,
            title=body.title,
            goal=body.goal,
            context=body.context,
            status=PlaybookStatus.QUEUED.value,
            priority=body.priority,
            tags=json.dumps(body.tags),
            created_at=now,
            updated_at=now,
        )
        session.add(row)

        for step in steps:
            step_row = PlaybookStepRow(
                id=step.id,
                playbook_id=playbook_id,
                title=step.title,
                description=step.description,
                agent_role=step.agent_role.value if hasattr(step.agent_role, "value") else str(step.agent_role),
                status=TaskStatus.PENDING.value,
                order_num=step.order,
                dependencies=json.dumps(step.dependencies),
            )
            session.add(step_row)

        await session.commit()

    playbook = Playbook(
        id=playbook_id,
        title=body.title,
        goal=body.goal,
        context=body.context,
        status=PlaybookStatus.QUEUED,
        priority=body.priority,
        tags=body.tags,
        steps=steps,
        created_at=now,
        updated_at=now,
    )

    logger.info("Created playbook %s with %d steps", playbook_id, len(steps))
    return playbook


@router.get("/", response_model=List[Playbook])
async def list_playbooks(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    status: Optional[str] = Query(default=None),
) -> List[Playbook]:
    """List playbooks with pagination and optional status filter."""
    if async_session_factory is None:
        return []

    async with async_session_factory() as session:
        query = select(PlaybookRow).order_by(PlaybookRow.created_at.desc())
        if status:
            query = query.where(PlaybookRow.status == status)
        query = query.offset(offset).limit(limit)

        result = await session.execute(query)
        rows = result.scalars().all()

    playbooks: List[Playbook] = []
    for row in rows:
        playbooks.append(Playbook(
            id=row.id,
            title=row.title,
            goal=row.goal,
            context=row.context,
            status=PlaybookStatus(row.status) if row.status in [s.value for s in PlaybookStatus] else PlaybookStatus.DRAFT,
            priority=row.priority,
            tags=json.loads(row.tags) if row.tags else [],
            created_at=row.created_at,
            updated_at=row.updated_at,
            completed_at=row.completed_at,
            total_tokens=row.total_tokens,
            error=row.error,
        ))

    return playbooks


@router.get("/{playbook_id}", response_model=Playbook)
async def get_playbook(playbook_id: str) -> Playbook:
    """Get a single playbook with its steps."""
    if async_session_factory is None:
        raise HTTPException(status_code=503, detail="Database not available")

    async with async_session_factory() as session:
        result = await session.execute(
            select(PlaybookRow).where(PlaybookRow.id == playbook_id)
        )
        row = result.scalar_one_or_none()
        if row is None:
            raise HTTPException(status_code=404, detail="Playbook not found")

        # Fetch steps
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
            started_at=s.started_at,
            completed_at=s.completed_at,
            retries=s.retries,
        )
        for s in step_rows
    ]

    return Playbook(
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
        total_tokens=row.total_tokens,
        error=row.error,
    )


@router.get("/{playbook_id}/status")
async def get_playbook_status(playbook_id: str) -> Dict[str, Any]:
    """Get playbook execution status with progress percentage."""
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
            select(PlaybookStepRow).where(PlaybookStepRow.playbook_id == playbook_id)
        )
        step_rows = steps_result.scalars().all()

    total = len(step_rows)
    completed = sum(1 for s in step_rows if s.status == TaskStatus.COMPLETED.value)
    failed = sum(1 for s in step_rows if s.status == TaskStatus.FAILED.value)
    running = sum(1 for s in step_rows if s.status == TaskStatus.RUNNING.value)
    progress = (completed / total * 100) if total > 0 else 0.0

    return {
        "playbook_id": playbook_id,
        "status": row.status,
        "progress_percent": round(progress, 1),
        "total_steps": total,
        "completed": completed,
        "failed": failed,
        "running": running,
        "pending": total - completed - failed - running,
    }


@router.get("/{playbook_id}/graph", response_model=TaskGraph)
async def get_playbook_graph(playbook_id: str) -> TaskGraph:
    """Get the task graph (nodes + edges) for visualization."""
    if async_session_factory is None:
        raise HTTPException(status_code=503, detail="Database not available")

    async with async_session_factory() as session:
        result = await session.execute(
            select(PlaybookStepRow)
            .where(PlaybookStepRow.playbook_id == playbook_id)
            .order_by(PlaybookStepRow.order_num)
        )
        step_rows = result.scalars().all()

    if not step_rows:
        raise HTTPException(status_code=404, detail="Playbook not found or has no steps")

    nodes: List[GraphNode] = []
    edges: List[GraphEdge] = []

    for i, step in enumerate(step_rows):
        nodes.append(GraphNode(
            id=step.id,
            label=step.title,
            role=step.agent_role,
            status=step.status,
            position=GraphPosition(x=float(i * 200), y=float((i % 3) * 100)),
        ))

        # Create edges from dependencies
        deps = json.loads(step.dependencies) if step.dependencies else []
        for dep_id in deps:
            edges.append(GraphEdge(source=dep_id, target=step.id))

        # If no explicit deps and not first, link to previous
        if not deps and i > 0:
            edges.append(GraphEdge(source=step_rows[i - 1].id, target=step.id))

    return TaskGraph(playbook_id=playbook_id, nodes=nodes, edges=edges)


@router.post("/{playbook_id}/rerun", response_model=Dict[str, str])
async def rerun_playbook(playbook_id: str) -> Dict[str, str]:
    """Rerun a playbook by resetting steps and re-queuing."""
    if async_session_factory is None:
        raise HTTPException(status_code=503, detail="Database not available")

    now = datetime.utcnow()

    async with async_session_factory() as session:
        result = await session.execute(
            select(PlaybookRow).where(PlaybookRow.id == playbook_id)
        )
        row = result.scalar_one_or_none()
        if row is None:
            raise HTTPException(status_code=404, detail="Playbook not found")

        # Reset playbook status
        await session.execute(
            update(PlaybookRow)
            .where(PlaybookRow.id == playbook_id)
            .values(
                status=PlaybookStatus.QUEUED.value,
                error=None,
                completed_at=None,
                updated_at=now,
            )
        )

        # Reset all steps
        await session.execute(
            update(PlaybookStepRow)
            .where(PlaybookStepRow.playbook_id == playbook_id)
            .values(
                status=TaskStatus.PENDING.value,
                output=None,
                error=None,
                started_at=None,
                completed_at=None,
                retries=0,
            )
        )

        await session.commit()

    logger.info("Rerun queued for playbook %s", playbook_id)
    return {"status": "queued", "playbook_id": playbook_id}


@router.delete("/{playbook_id}")
async def delete_playbook(playbook_id: str) -> Dict[str, str]:
    """Delete a playbook and all its steps."""
    if async_session_factory is None:
        raise HTTPException(status_code=503, detail="Database not available")

    async with async_session_factory() as session:
        result = await session.execute(
            select(PlaybookRow).where(PlaybookRow.id == playbook_id)
        )
        if result.scalar_one_or_none() is None:
            raise HTTPException(status_code=404, detail="Playbook not found")

        await session.execute(
            delete(PlaybookStepRow).where(PlaybookStepRow.playbook_id == playbook_id)
        )
        await session.execute(
            delete(PlaybookRow).where(PlaybookRow.id == playbook_id)
        )
        await session.commit()

    logger.info("Deleted playbook %s", playbook_id)
    return {"status": "deleted", "playbook_id": playbook_id}
