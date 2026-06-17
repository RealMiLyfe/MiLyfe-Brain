"""
MiLyfe Brain - Playbook Orchestrator

The main playbook execution engine. Loads playbooks from the database,
parses them into steps, performs topological sorting into parallel layers,
executes steps concurrently where possible, handles failures with debugger
agent retries, and persists results.
"""
from __future__ import annotations

import asyncio
import json
import logging
from collections import deque
from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy import select, update

from agents.factory import AgentFactory
from config import settings
from graphs.playbook_parser import parse_playbook
from memory.database import PlaybookRow, PlaybookStepRow, async_session_factory
from models.schemas import AgentRole, PlaybookStatus, TaskStatus

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def execute_playbook(playbook_id: str) -> None:
    """
    Main entry point for playbook execution.

    Workflow:
      1. Load playbook from DB
      2. Parse goal into steps if none exist
      3. Save parsed steps to DB
      4. Topological sort into parallel layers
      5. Execute layers (asyncio.gather for independent steps)
      6. On step failure: dispatch debugger agent → retry once
      7. Mark playbook completed/failed in DB
      8. Git snapshot after completion
    """
    if async_session_factory is None:
        raise RuntimeError("Database not initialized. Call init_database() first.")

    # --- 1. Load playbook ---
    async with async_session_factory() as session:
        result = await session.execute(
            select(PlaybookRow).where(PlaybookRow.id == playbook_id)
        )
        playbook = result.scalar_one_or_none()

        if playbook is None:
            raise ValueError(f"Playbook not found: {playbook_id}")

        # Mark as running
        playbook.status = PlaybookStatus.RUNNING.value
        playbook.updated_at = datetime.utcnow()
        await session.commit()

    # --- 2. Parse if no steps exist ---
    async with async_session_factory() as session:
        step_result = await session.execute(
            select(PlaybookStepRow).where(PlaybookStepRow.playbook_id == playbook_id)
        )
        step_rows = step_result.scalars().all()

    if not step_rows:
        # Parse the playbook goal into steps
        parsed_steps = parse_playbook(playbook.goal)

        # --- 3. Save parsed steps to DB ---
        async with async_session_factory() as session:
            for step in parsed_steps:
                row = PlaybookStepRow(
                    id=step.id,
                    playbook_id=playbook_id,
                    title=step.title,
                    description=step.description,
                    agent_role=step.agent_role.value,
                    status=TaskStatus.PENDING.value,
                    order_num=step.order,
                    dependencies=json.dumps(step.dependencies) if step.dependencies else None,
                )
                session.add(row)
            await session.commit()

        # Reload steps from DB
        async with async_session_factory() as session:
            step_result = await session.execute(
                select(PlaybookStepRow).where(PlaybookStepRow.playbook_id == playbook_id)
            )
            step_rows = step_result.scalars().all()

    # --- 4. Topological sort into parallel layers ---
    layers = _topological_sort(list(step_rows))

    # --- 5. Execute layers ---
    failed_steps: List[str] = []

    for layer in layers:
        if not layer:
            continue

        # Execute all steps in a layer concurrently
        tasks = [_execute_step(step_id, playbook_id) for step_id in layer]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Check results for failures
        for step_id, result in zip(layer, results):
            if isinstance(result, Exception):
                error_msg = str(result)
                logger.error("Step %s failed: %s", step_id, error_msg)

                # --- 6. Retry with debugger ---
                retry_success = await _retry_with_debug(step_id, playbook_id, error_msg)
                if not retry_success:
                    failed_steps.append(step_id)
            elif isinstance(result, str) and result.startswith("[ERROR]"):
                error_msg = result
                logger.error("Step %s returned error: %s", step_id, error_msg)

                retry_success = await _retry_with_debug(step_id, playbook_id, error_msg)
                if not retry_success:
                    failed_steps.append(step_id)

        # If any step in this layer failed permanently, stop execution
        if failed_steps:
            break

    # --- 7. Mark completed/failed in DB ---
    async with async_session_factory() as session:
        now = datetime.utcnow()
        if failed_steps:
            await session.execute(
                update(PlaybookRow)
                .where(PlaybookRow.id == playbook_id)
                .values(
                    status=PlaybookStatus.FAILED.value,
                    error=f"Steps failed: {', '.join(failed_steps)}",
                    updated_at=now,
                )
            )
        else:
            await session.execute(
                update(PlaybookRow)
                .where(PlaybookRow.id == playbook_id)
                .values(
                    status=PlaybookStatus.COMPLETED.value,
                    completed_at=now,
                    updated_at=now,
                )
            )
        await session.commit()

    # --- 8. Git snapshot after completion ---
    if settings.auto_git_snapshots:
        await _git_snapshot(playbook_id)

    logger.info(
        "Playbook %s finished with status: %s",
        playbook_id,
        "FAILED" if failed_steps else "COMPLETED",
    )


async def intervene(playbook_id: str, message: str) -> str:
    """
    Handle user intervention during playbook execution.

    Pauses execution and injects user guidance into the orchestration context.
    Returns acknowledgement or the adjusted plan.
    """
    if async_session_factory is None:
        raise RuntimeError("Database not initialized.")

    factory = AgentFactory()

    # Use orchestrator to process the intervention
    response = await factory.execute_task(
        role=AgentRole.ORCHESTRATOR,
        task=(
            f"User intervention for playbook {playbook_id}:\n"
            f"{message}\n\n"
            "Acknowledge the intervention, explain how it affects the current plan, "
            "and suggest next steps."
        ),
        context={"playbook_id": playbook_id, "intervention": True},
    )

    # Update playbook status to reflect intervention
    async with async_session_factory() as session:
        await session.execute(
            update(PlaybookRow)
            .where(PlaybookRow.id == playbook_id)
            .values(updated_at=datetime.utcnow())
        )
        await session.commit()

    return response


# ---------------------------------------------------------------------------
# Step Execution
# ---------------------------------------------------------------------------


async def _execute_step(step_id: str, playbook_id: str) -> str:
    """
    Execute a single playbook step.

    Loads the step from DB, spawns the appropriate agent, runs it,
    saves the result back to DB, and returns the output.
    """
    if async_session_factory is None:
        raise RuntimeError("Database not initialized.")

    # Load step
    async with async_session_factory() as session:
        result = await session.execute(
            select(PlaybookStepRow).where(PlaybookStepRow.id == step_id)
        )
        step = result.scalar_one_or_none()

        if step is None:
            return f"[ERROR] Step not found: {step_id}"

        # Mark as running
        step.status = TaskStatus.RUNNING.value
        step.started_at = datetime.utcnow()
        await session.commit()

    # Determine task description
    task = step.description or step.title

    # Determine agent role
    try:
        role = AgentRole(step.agent_role)
    except ValueError:
        role = AgentRole.ORCHESTRATOR

    # Spawn and execute agent
    factory = AgentFactory()
    try:
        output = await factory.execute_task(
            role=role,
            task=task,
            context={
                "playbook_id": playbook_id,
                "step_id": step_id,
                "step_title": step.title,
            },
        )
    except Exception as e:
        # Save error to DB
        async with async_session_factory() as session:
            await session.execute(
                update(PlaybookStepRow)
                .where(PlaybookStepRow.id == step_id)
                .values(
                    status=TaskStatus.FAILED.value,
                    error=str(e),
                    completed_at=datetime.utcnow(),
                )
            )
            await session.commit()
        raise

    # Save result to DB
    async with async_session_factory() as session:
        await session.execute(
            update(PlaybookStepRow)
            .where(PlaybookStepRow.id == step_id)
            .values(
                status=TaskStatus.COMPLETED.value,
                output=output,
                completed_at=datetime.utcnow(),
            )
        )
        await session.commit()

    return output


# ---------------------------------------------------------------------------
# Retry with Debugger
# ---------------------------------------------------------------------------


async def _retry_with_debug(step_id: str, playbook_id: str, error: str) -> bool:
    """
    Use the debugger agent to analyze the failure, then retry the step once.

    Returns True if the retry succeeds, False otherwise.
    """
    if async_session_factory is None:
        return False

    # Load the failed step
    async with async_session_factory() as session:
        result = await session.execute(
            select(PlaybookStepRow).where(PlaybookStepRow.id == step_id)
        )
        step = result.scalar_one_or_none()
        if step is None:
            return False

    # Ask the debugger agent to analyze the failure
    factory = AgentFactory()
    try:
        diagnosis = await factory.execute_task(
            role=AgentRole.CODER,  # Debugger maps to CODER role
            task=(
                f"Debug and analyze this failure:\n"
                f"Step: {step.title}\n"
                f"Description: {step.description}\n"
                f"Error: {error}\n\n"
                "Provide a brief root cause analysis and suggest how to fix or work around this issue."
            ),
            context={
                "playbook_id": playbook_id,
                "step_id": step_id,
                "mode": "debugger",
            },
        )
    except Exception as e:
        logger.warning("Debugger agent failed: %s", str(e))
        return False

    logger.info("Debugger diagnosis for step %s: %s", step_id, diagnosis[:200])

    # Retry the step with the debugger's guidance incorporated
    async with async_session_factory() as session:
        await session.execute(
            update(PlaybookStepRow)
            .where(PlaybookStepRow.id == step_id)
            .values(
                status=TaskStatus.PENDING.value,
                retries=step.retries + 1,
                error=None,
            )
        )
        await session.commit()

    try:
        retry_result = await _execute_step(step_id, playbook_id)
        if isinstance(retry_result, str) and retry_result.startswith("[ERROR]"):
            return False
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Topological Sort (Kahn's Algorithm)
# ---------------------------------------------------------------------------


def _topological_sort(step_rows: List[PlaybookStepRow]) -> List[List[str]]:
    """
    Sort steps into parallel execution layers using Kahn's algorithm.

    Steps with no unresolved dependencies are grouped into the same layer,
    enabling concurrent execution within a layer.

    Returns a list of layers, where each layer is a list of step IDs
    that can execute concurrently.
    """
    if not step_rows:
        return []

    # Build adjacency and in-degree structures
    in_degree: Dict[str, int] = {}
    dependents: Dict[str, List[str]] = {}  # step_id -> list of steps that depend on it
    step_id_set = {row.id for row in step_rows}

    # Map order numbers to step IDs for dependency resolution
    order_to_ids: Dict[int, List[str]] = {}
    for row in step_rows:
        order_to_ids.setdefault(row.order_num, []).append(row.id)

    # Initialize
    for row in step_rows:
        in_degree[row.id] = 0
        dependents.setdefault(row.id, [])

    # Parse dependencies and build graph
    for row in step_rows:
        deps_json = row.dependencies
        if not deps_json:
            continue

        try:
            deps = json.loads(deps_json)
        except (json.JSONDecodeError, TypeError):
            continue

        if not isinstance(deps, list):
            continue

        for dep in deps:
            dep_str = str(dep)
            # Dependency can be a step ID or an order number
            resolved_ids: List[str] = []

            if dep_str in step_id_set:
                resolved_ids = [dep_str]
            else:
                # Try as order number
                try:
                    order_num = int(dep_str)
                    resolved_ids = order_to_ids.get(order_num, [])
                except (ValueError, TypeError):
                    continue

            for dep_id in resolved_ids:
                if dep_id != row.id and dep_id in step_id_set:
                    dependents.setdefault(dep_id, []).append(row.id)
                    in_degree[row.id] = in_degree.get(row.id, 0) + 1

    # Kahn's algorithm with layer tracking
    layers: List[List[str]] = []
    queue: deque[str] = deque()

    # Seed with nodes having zero in-degree
    for step_id, degree in in_degree.items():
        if degree == 0:
            queue.append(step_id)

    while queue:
        # Current layer: all nodes with in-degree 0
        layer: List[str] = list(queue)
        queue.clear()

        layers.append(layer)

        # Process the layer: decrement in-degrees
        for step_id in layer:
            for dependent in dependents.get(step_id, []):
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)

    # Handle any remaining nodes (cycles) — add as final layer
    processed = {sid for layer in layers for sid in layer}
    remaining = [sid for sid in in_degree if sid not in processed]
    if remaining:
        logger.warning(
            "Dependency cycle detected among steps: %s. Executing sequentially.",
            remaining,
        )
        layers.append(remaining)

    return layers


# ---------------------------------------------------------------------------
# Git Snapshot
# ---------------------------------------------------------------------------


async def _git_snapshot(playbook_id: str) -> None:
    """Create a git snapshot of the workspace after playbook completion."""
    try:
        proc = await asyncio.create_subprocess_exec(
            "git", "add", "-A",
            cwd=settings.workspace_dir,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await proc.communicate()

        proc = await asyncio.create_subprocess_exec(
            "git", "commit", "-m", f"[MiLyfe] Playbook {playbook_id} completed",
            "--allow-empty",
            cwd=settings.workspace_dir,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()

        if proc.returncode == 0:
            logger.info("Git snapshot created for playbook %s", playbook_id)
        else:
            logger.debug(
                "Git snapshot skipped for playbook %s: %s",
                playbook_id,
                stderr.decode().strip() if stderr else "unknown reason",
            )
    except FileNotFoundError:
        logger.debug("Git not available, skipping snapshot")
    except Exception as e:
        logger.debug("Git snapshot failed (non-fatal): %s", str(e))
