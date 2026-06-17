"""Playbooks API — CRUD and execution management."""

import json
import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from memory.database import PlaybookModel, PlaybookStepModel, get_db
from models.schemas import (
    GraphEdge,
    GraphNode,
    Playbook,
    PlaybookCreate,
    PlaybookStep,
    TaskStatus,
)
from graphs.playbook_parser import playbook_parser
from services.queue_manager import queue_manager

router = APIRouter()


@router.post("/", response_model=Playbook, status_code=201)
async def create_playbook(
    body: PlaybookCreate, db: AsyncSession = Depends(get_db)
) -> Playbook:
    """Create a new playbook, optionally parsing raw_text into steps."""
    playbook_id = str(uuid.uuid4())

    # Parse steps from raw_text if no explicit steps provided
    steps = body.steps
    if not steps and body.raw_text:
        steps = await playbook_parser.parse(body.raw_text)

    # Create DB record
    db_playbook = PlaybookModel(
        id=playbook_id,
        title=body.title,
        description=body.description,
        raw_text=body.raw_text,
        status="pending",
        created_at=datetime.utcnow(),
    )
    db.add(db_playbook)

    # Create step records
    for i, step in enumerate(steps):
        db_step = PlaybookStepModel(
            id=step.id or str(uuid.uuid4()),
            playbook_id=playbook_id,
            description=step.description,
            agent_role=step.agent_role.value if step.agent_role else None,
            status="pending",
            order_index=i,
            depends_on=json.dumps(step.depends_on) if step.depends_on else None,
            complexity=step.complexity.value if step.complexity else "medium",
        )
        db.add(db_step)

    await db.commit()

    # Auto-execute if requested
    if body.auto_execute:
        await queue_manager.enqueue(playbook_id)

    return Playbook(
        id=playbook_id,
        title=body.title,
        description=body.description,
        status=TaskStatus.pending,
        steps=steps,
        raw_text=body.raw_text,
        created_at=datetime.utcnow(),
    )


@router.get("/", response_model=List[Playbook])
async def list_playbooks(db: AsyncSession = Depends(get_db)) -> List[Playbook]:
    """List all playbooks ordered by creation date."""
    result = await db.execute(
        select(PlaybookModel).order_by(PlaybookModel.created_at.desc())
    )
    rows = result.scalars().all()

    playbooks = []
    for row in rows:
        steps = [
            PlaybookStep(
                id=s.id,
                description=s.description,
                agent_role=s.agent_role,
                depends_on=json.loads(s.depends_on) if s.depends_on else [],
                complexity=s.complexity or "medium",
            )
            for s in (row.steps or [])
        ]
        playbooks.append(Playbook(
            id=row.id,
            title=row.title,
            description=row.description or "",
            status=row.status,
            steps=steps,
            raw_text=row.raw_text,
            created_at=row.created_at,
            completed_at=row.completed_at,
            error=row.error,
        ))

    return playbooks


@router.get("/{playbook_id}", response_model=Playbook)
async def get_playbook(
    playbook_id: str, db: AsyncSession = Depends(get_db)
) -> Playbook:
    """Get a single playbook by ID."""
    result = await db.execute(
        select(PlaybookModel).where(PlaybookModel.id == playbook_id)
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Playbook not found")

    steps = [
        PlaybookStep(
            id=s.id,
            description=s.description,
            agent_role=s.agent_role,
            depends_on=json.loads(s.depends_on) if s.depends_on else [],
            complexity=s.complexity or "medium",
        )
        for s in (row.steps or [])
    ]

    return Playbook(
        id=row.id,
        title=row.title,
        description=row.description or "",
        status=row.status,
        steps=steps,
        raw_text=row.raw_text,
        created_at=row.created_at,
        completed_at=row.completed_at,
        error=row.error,
    )


@router.get("/{playbook_id}/status")
async def get_playbook_status(
    playbook_id: str, db: AsyncSession = Depends(get_db)
) -> dict:
    """Get playbook execution status with step progress."""
    result = await db.execute(
        select(PlaybookModel).where(PlaybookModel.id == playbook_id)
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Playbook not found")

    steps = row.steps or []
    completed = sum(1 for s in steps if s.status == "completed")
    failed = sum(1 for s in steps if s.status == "failed")
    running = sum(1 for s in steps if s.status == "running")

    return {
        "id": row.id,
        "status": row.status,
        "total_steps": len(steps),
        "completed_steps": completed,
        "failed_steps": failed,
        "running_steps": running,
        "progress": completed / len(steps) if steps else 0,
    }


@router.get("/{playbook_id}/graph")
async def get_playbook_graph(
    playbook_id: str, db: AsyncSession = Depends(get_db)
) -> dict:
    """Get playbook as a graph (nodes + edges) for visualization."""
    result = await db.execute(
        select(PlaybookModel).where(PlaybookModel.id == playbook_id)
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Playbook not found")

    nodes = []
    edges = []

    for i, step in enumerate(row.steps or []):
        nodes.append(GraphNode(
            id=step.id,
            label=step.description[:50],
            type=step.agent_role or "default",
            status=step.status,
            position={"x": 100, "y": i * 120},
            data={"full_description": step.description, "role": step.agent_role},
        ))

        deps = json.loads(step.depends_on) if step.depends_on else []
        for dep_id in deps:
            edges.append(GraphEdge(
                id=f"{dep_id}-{step.id}",
                source=dep_id,
                target=step.id,
                animated=step.status == "running",
            ))

    return {
        "nodes": [n.model_dump() for n in nodes],
        "edges": [e.model_dump() for e in edges],
    }


@router.post("/{playbook_id}/rerun")
async def rerun_playbook(
    playbook_id: str, db: AsyncSession = Depends(get_db)
) -> dict:
    """Re-run a playbook by resetting its status and re-queueing."""
    result = await db.execute(
        select(PlaybookModel).where(PlaybookModel.id == playbook_id)
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Playbook not found")

    # Reset playbook status
    row.status = "pending"
    row.error = None
    row.completed_at = None

    # Reset step statuses
    for step in (row.steps or []):
        step.status = "pending"
        step.result = None
        step.started_at = None
        step.completed_at = None

    await db.commit()
    await queue_manager.enqueue(playbook_id)

    return {"message": "Playbook re-queued", "playbook_id": playbook_id}


@router.delete("/{playbook_id}")
async def delete_playbook(
    playbook_id: str, db: AsyncSession = Depends(get_db)
) -> dict:
    """Delete a playbook and all its steps."""
    result = await db.execute(
        select(PlaybookModel).where(PlaybookModel.id == playbook_id)
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Playbook not found")

    await db.delete(row)
    await db.commit()

    return {"message": "Playbook deleted", "playbook_id": playbook_id}
