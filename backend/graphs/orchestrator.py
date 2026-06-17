"""MiLyfe Brain — Orchestrator (Step Executor with parallel, retry, debug)."""

from __future__ import annotations

import asyncio
import uuid
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

import orjson
import structlog
from sqlalchemy import select

from config import settings
from models.schemas import (
    AgentRole,
    EventType,
    PlaybookStatus,
    PlaybookStep,
    TaskComplexity,
    TaskStatus,
)

logger = structlog.get_logger()


async def execute_playbook(playbook_id: str):
    """Main entry point: execute a playbook end-to-end.

    Flow:
    1. Load playbook from DB
    2. Parse if no steps exist
    3. Topological sort by dependencies
    4. Execute in parallel layers
    5. Handle failures with debugger agent
    """
    from memory.database import PlaybookRow, PlaybookStepRow, async_session_factory

    # Emit start event
    _emit(EventType.PLAYBOOK_STARTED, playbook_id=playbook_id)

    # 1. Load playbook
    async with async_session_factory() as session:
        playbook = await session.get(PlaybookRow, playbook_id)
        if not playbook:
            raise ValueError(f"Playbook not found: {playbook_id}")

        playbook.status = "running"
        playbook.started_at = datetime.utcnow()
        await session.commit()

    # 2. Parse if needed (no steps yet)
    async with async_session_factory() as session:
        steps_result = await session.execute(
            select(PlaybookStepRow).where(
                PlaybookStepRow.playbook_id == playbook_id
            ).order_by(PlaybookStepRow.order_index)
        )
        step_rows = steps_result.scalars().all()

    if not step_rows:
        # Parse the playbook text into steps
        from graphs.playbook_parser import parse_playbook

        text = playbook.raw_text or playbook.description
        parsed_steps = await parse_playbook(text, model=playbook.model_override)

        # Save parsed steps to DB
        async with async_session_factory() as session:
            for idx, step in enumerate(parsed_steps):
                row = PlaybookStepRow(
                    id=step.id or str(uuid.uuid4()),
                    playbook_id=playbook_id,
                    description=step.description,
                    agent_role=step.agent_role.value if step.agent_role else None,
                    status="pending",
                    depends_on=orjson.dumps(step.depends_on).decode(),
                    complexity=step.complexity.value if step.complexity else "medium",
                    tools_needed=orjson.dumps(step.tools_needed).decode(),
                    order_index=idx,
                )
                session.add(row)
            await session.commit()

        # Reload
        async with async_session_factory() as session:
            steps_result = await session.execute(
                select(PlaybookStepRow).where(
                    PlaybookStepRow.playbook_id == playbook_id
                ).order_by(PlaybookStepRow.order_index)
            )
            step_rows = steps_result.scalars().all()

    # 3. Build dependency graph and sort into layers
    layers = _topological_sort(step_rows)
    logger.info("orchestrator_layers", playbook_id=playbook_id, layer_count=len(layers))

    # 4. Execute layers
    try:
        for layer_idx, layer in enumerate(layers):
            logger.info("executing_layer", layer=layer_idx, steps=len(layer))

            # Execute all steps in this layer in parallel
            tasks = [
                _execute_step(step_id, playbook_id)
                for step_id in layer
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Check for failures
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    step_id = layer[i]
                    logger.error("step_failed", step_id=step_id, error=str(result))

                    # Try debug + retry
                    success = await _retry_with_debug(step_id, playbook_id, str(result))
                    if not success:
                        # Mark playbook as failed
                        async with async_session_factory() as session:
                            pb = await session.get(PlaybookRow, playbook_id)
                            if pb:
                                pb.status = "failed"
                                pb.error = f"Step {step_id} failed: {result}"
                                pb.completed_at = datetime.utcnow()
                                await session.commit()
                        _emit(EventType.ERROR, playbook_id=playbook_id,
                              data={"step_id": step_id, "error": str(result)})
                        return

        # All done!
        async with async_session_factory() as session:
            pb = await session.get(PlaybookRow, playbook_id)
            if pb:
                pb.status = "completed"
                pb.completed_at = datetime.utcnow()
                await session.commit()

        _emit(EventType.PLAYBOOK_COMPLETED, playbook_id=playbook_id)
        logger.info("playbook_completed", playbook_id=playbook_id)

        # Snapshot workspace
        try:
            from services.workspace_git import workspace_git
            await workspace_git.snapshot(f"Playbook completed: {playbook_id[:8]}")
        except Exception:
            pass

    except Exception as e:
        logger.error("orchestrator_error", playbook_id=playbook_id, error=str(e))
        async with async_session_factory() as session:
            pb = await session.get(PlaybookRow, playbook_id)
            if pb:
                pb.status = "failed"
                pb.error = str(e)
                pb.completed_at = datetime.utcnow()
                await session.commit()


async def _execute_step(step_id: str, playbook_id: str) -> str:
    """Execute a single step using the appropriate agent."""
    from agents.factory import agent_factory
    from memory.database import PlaybookStepRow, async_session_factory

    # Load step
    async with async_session_factory() as session:
        step = await session.get(PlaybookStepRow, step_id)
        if not step:
            raise ValueError(f"Step not found: {step_id}")

        step.status = "running"
        step.started_at = datetime.utcnow()
        await session.commit()

    _emit(EventType.STEP_STARTED, playbook_id=playbook_id,
          data={"step_id": step_id, "description": step.description})

    # Determine role and model
    role = AgentRole(step.agent_role) if step.agent_role else AgentRole.CODER
    model = None
    if step.complexity == "heavy":
        model = settings.default_heavy_model
    elif step.complexity == "light":
        model = settings.default_light_model

    # Execute via agent
    try:
        result = await agent_factory.execute_task(
            role=role,
            task=step.description,
            context={"playbook_id": playbook_id, "step_id": step_id},
            model_override=model,
        )

        # Mark completed
        async with async_session_factory() as session:
            step_row = await session.get(PlaybookStepRow, step_id)
            if step_row:
                step_row.status = "completed"
                step_row.result = result[:5000] if result else ""
                step_row.completed_at = datetime.utcnow()
                await session.commit()

        _emit(EventType.STEP_COMPLETED, playbook_id=playbook_id,
              data={"step_id": step_id, "result_preview": result[:200] if result else ""})

        return result

    except Exception as e:
        # Mark failed
        async with async_session_factory() as session:
            step_row = await session.get(PlaybookStepRow, step_id)
            if step_row:
                step_row.status = "failed"
                step_row.error = str(e)
                step_row.completed_at = datetime.utcnow()
                await session.commit()
        raise


async def _retry_with_debug(step_id: str, playbook_id: str, error: str) -> bool:
    """Use debugger agent to analyze failure, then retry once."""
    from agents.factory import agent_factory
    from memory.database import PlaybookStepRow, async_session_factory

    if settings.max_retries <= 0:
        return False

    logger.info("retry_with_debug", step_id=step_id)

    # Load step
    async with async_session_factory() as session:
        step = await session.get(PlaybookStepRow, step_id)
        if not step:
            return False

    # Ask debugger to analyze
    debug_prompt = f"""A step failed during playbook execution.

Step description: {step.description}
Error: {error}

Analyze the error and suggest how to fix it. Then provide the corrected approach."""

    try:
        fix_suggestion = await agent_factory.execute_task(
            role=AgentRole.DEBUGGER,
            task=debug_prompt,
            context={"playbook_id": playbook_id, "retry": True},
        )

        # Retry the step with the fix context
        async with async_session_factory() as session:
            step_row = await session.get(PlaybookStepRow, step_id)
            if step_row:
                step_row.status = "running"
                step_row.error = None
                await session.commit()

        role = AgentRole(step.agent_role) if step.agent_role else AgentRole.CODER
        retry_task = f"{step.description}\n\nPrevious attempt failed: {error}\nFix suggestion: {fix_suggestion[:500]}"

        result = await agent_factory.execute_task(
            role=role,
            task=retry_task,
            context={"playbook_id": playbook_id, "retry": True},
        )

        # Mark completed
        async with async_session_factory() as session:
            step_row = await session.get(PlaybookStepRow, step_id)
            if step_row:
                step_row.status = "completed"
                step_row.result = result[:5000] if result else ""
                step_row.completed_at = datetime.utcnow()
                await session.commit()

        return True

    except Exception as e:
        logger.error("retry_failed", step_id=step_id, error=str(e))
        return False


async def intervene(playbook_id: str, message: str) -> str:
    """Allow user to intervene in a running playbook."""
    from agents.factory import agent_factory

    return await agent_factory.execute_task(
        role=AgentRole.ORCHESTRATOR,
        task=f"User intervention for playbook {playbook_id}: {message}",
        context={"playbook_id": playbook_id, "intervention": True},
    )


def _topological_sort(step_rows: list) -> List[List[str]]:
    """Sort steps into parallel execution layers based on dependencies."""
    # Build dependency graph
    all_ids = {s.id for s in step_rows}
    deps: Dict[str, Set[str]] = {}

    for s in step_rows:
        step_deps = set()
        if s.depends_on:
            try:
                parsed = orjson.loads(s.depends_on)
                step_deps = set(parsed) & all_ids  # Only valid deps
            except Exception:
                pass
        deps[s.id] = step_deps

    # Kahn's algorithm for topological sort into layers
    layers = []
    remaining = set(all_ids)
    completed = set()

    while remaining:
        # Find all steps with no unmet dependencies
        ready = {
            sid for sid in remaining
            if deps[sid].issubset(completed)
        }

        if not ready:
            # Circular dependency — break it by picking one
            ready = {next(iter(remaining))}
            logger.warning("circular_dependency_broken", step=next(iter(ready)))

        layers.append(sorted(ready))  # Sort for determinism
        completed.update(ready)
        remaining -= ready

    return layers


def _emit(event_type: EventType, playbook_id: str = None, data: dict = None):
    """Emit orchestration event."""
    try:
        from api.routes.streaming import emit_event
        emit_event(event_type=event_type, playbook_id=playbook_id, data=data or {})
    except Exception:
        pass
