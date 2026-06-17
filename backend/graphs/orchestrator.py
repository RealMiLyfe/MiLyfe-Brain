"""Orchestrator — Step executor for playbook execution.

Loads playbooks, determines execution layers via topological sort,
executes steps in parallel within each layer, and handles retries.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections import defaultdict, deque
from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from memory.database import async_session_factory, PlaybookModel, PlaybookStepModel
from agents.base import AgentRole
from agents.factory import get_agent_factory
from agents.message_bus import Topic, get_message_bus
from models.schemas import StreamEvent

logger = logging.getLogger(__name__)


class Orchestrator:
    """Executes playbooks by parsing steps, sorting layers, and running agents.

    Responsibilities:
    - Load playbook from DB
    - Parse step dependencies into execution layers (topological sort)
    - Execute steps in parallel within each layer using asyncio.gather
    - Spawn agents via AgentFactory for each step
    - On failure: spawn DebuggerAgent for 1 retry
    - Update step/playbook status in DB throughout
    - Emit StreamEvents for frontend via message bus
    """

    def __init__(self) -> None:
        self._bus = get_message_bus()

    async def execute_playbook(self, playbook_id: str) -> None:
        """Execute all steps of a playbook in dependency order.

        Args:
            playbook_id: UUID of the playbook to execute.
        """
        async with async_session_factory() as db:
            # Load playbook
            result = await db.execute(
                select(PlaybookModel).where(PlaybookModel.id == playbook_id)
            )
            playbook = result.scalar_one_or_none()
            if playbook is None:
                logger.error("Playbook %s not found", playbook_id)
                return

            # Update playbook status to running
            playbook.status = "running"
            await db.commit()

            await self._emit_event("playbook_started", playbook_id=playbook_id)

            # Load steps
            steps_result = await db.execute(
                select(PlaybookStepModel)
                .where(PlaybookStepModel.playbook_id == playbook_id)
                .order_by(PlaybookStepModel.order_index)
            )
            steps = list(steps_result.scalars().all())

            if not steps:
                playbook.status = "completed"
                playbook.completed_at = datetime.utcnow()
                await db.commit()
                await self._emit_event("playbook_completed", playbook_id=playbook_id)
                return

            # Build execution layers
            layers = self._build_layers(steps)

            try:
                for layer_idx, layer in enumerate(layers):
                    logger.info(
                        "Playbook %s: executing layer %d with %d steps",
                        playbook_id, layer_idx, len(layer),
                    )

                    # Execute all steps in this layer in parallel with per-step timeout
                    step_timeout = settings.agent_timeout  # Default 300s
                    tasks = [
                        asyncio.wait_for(
                            self._execute_step(step, db, playbook_id),
                            timeout=step_timeout,
                        )
                        for step in layer
                    ]
                    results = await asyncio.gather(*tasks, return_exceptions=True)

                    # Check for failures
                    for i, result in enumerate(results):
                        if isinstance(result, asyncio.TimeoutError):
                            step = layer[i]
                            logger.error("Step %s timed out after %ds", step.id, step_timeout)
                            # Update step status in its own session
                            async with async_session_factory() as timeout_db:
                                from sqlalchemy import update as sa_update
                                await timeout_db.execute(
                                    sa_update(PlaybookStepModel)
                                    .where(PlaybookStepModel.id == step.id)
                                    .values(status="failed", result=f"Timed out after {step_timeout}s", completed_at=datetime.utcnow())
                                )
                                await timeout_db.commit()
                            await self._emit_event("step_failed", playbook_id=playbook_id, step_id=step.id, error=f"Timeout after {step_timeout}s")
                        elif isinstance(result, Exception):
                            step = layer[i]
                            logger.error("Step %s failed: %s", step.id, result)

                # Mark playbook completed
                playbook.status = "completed"
                playbook.completed_at = datetime.utcnow()
                await db.commit()
                await self._emit_event("playbook_completed", playbook_id=playbook_id)

                # Learn skill from successful playbook
                try:
                    from services.skill_library import skill_library
                    await skill_library.learn_from_playbook(playbook_id)
                except Exception as skill_err:
                    logger.debug("Skill learning failed (non-fatal): %s", skill_err)

            except Exception as e:
                playbook.status = "failed"
                playbook.error = str(e)
                playbook.completed_at = datetime.utcnow()
                await db.commit()
                await self._emit_event(
                    "playbook_failed", playbook_id=playbook_id, error=str(e)
                )
                logger.error("Playbook %s failed: %s", playbook_id, e, exc_info=True)

    def _build_layers(self, steps: List[PlaybookStepModel]) -> List[List[PlaybookStepModel]]:
        """Topological sort of steps into execution layers by depends_on.

        Steps with no dependencies go in layer 0. Steps depending on layer 0
        steps go in layer 1, etc.

        Returns:
            List of layers, each layer is a list of steps that can run in parallel.
        """
        step_map: Dict[str, PlaybookStepModel] = {s.id: s for s in steps}
        in_degree: Dict[str, int] = defaultdict(int)
        dependents: Dict[str, List[str]] = defaultdict(list)

        for step in steps:
            deps = self._parse_depends_on(step.depends_on)
            in_degree[step.id] = len(deps)
            for dep_id in deps:
                dependents[dep_id].append(step.id)

        # Start with steps that have no dependencies
        layers: List[List[PlaybookStepModel]] = []
        queue = deque([s.id for s in steps if in_degree[s.id] == 0])

        while queue:
            current_layer_ids = list(queue)
            queue.clear()
            current_layer = [step_map[sid] for sid in current_layer_ids if sid in step_map]
            layers.append(current_layer)

            for sid in current_layer_ids:
                for dependent_id in dependents.get(sid, []):
                    in_degree[dependent_id] -= 1
                    if in_degree[dependent_id] == 0:
                        queue.append(dependent_id)

        return layers

    def _parse_depends_on(self, depends_on: Optional[str]) -> List[str]:
        """Parse the depends_on JSON string into a list of step IDs."""
        if not depends_on:
            return []
        try:
            parsed = json.loads(depends_on)
            if isinstance(parsed, list):
                return [str(x) for x in parsed]
        except (json.JSONDecodeError, TypeError):
            pass
        return []

    async def _execute_step(
        self,
        step: PlaybookStepModel,
        db: AsyncSession,
        playbook_id: str,
    ) -> str:
        """Execute a single playbook step using an agent.

        Spawns the appropriate agent, calls think(), handles retry on failure.
        Uses its own DB session to avoid asyncio.gather session sharing issues.

        Returns:
            The agent's result string.
        """
        factory = get_agent_factory()

        # Use a dedicated session for this step to avoid concurrent session issues
        async with async_session_factory() as step_db:
            from sqlalchemy import select as sa_select

            # Re-load the step in our own session
            step_result = await step_db.execute(
                sa_select(PlaybookStepModel).where(PlaybookStepModel.id == step.id)
            )
            local_step = step_result.scalar_one()

            # Mark step as running
            local_step.status = "running"
            local_step.started_at = datetime.utcnow()
            await step_db.commit()

            await self._emit_event(
                "step_started",
                playbook_id=playbook_id,
                step_id=local_step.id,
                description=local_step.description,
            )

            role = local_step.agent_role or "coder"

            try:
                agent = factory.spawn(role=role, context={"playbook_id": playbook_id})
                result = await agent.think(local_step.description)

                # Mark completed
                local_step.status = "completed"
                local_step.result = result
                local_step.completed_at = datetime.utcnow()
                await step_db.commit()

                # Retire agent
                await factory.retire(agent.id)

                await self._emit_event(
                    "step_completed",
                    playbook_id=playbook_id,
                    step_id=local_step.id,
                    result_preview=result[:200] if result else "",
                )

                return result

            except Exception as e:
                logger.warning("Step %s failed, attempting debugger retry: %s", local_step.id, e)

                # Retry with DebuggerAgent (max 1 retry)
                try:
                    debugger = factory.spawn(
                        role="debugger",
                        context={
                            "playbook_id": playbook_id,
                            "original_error": str(e),
                            "original_role": role,
                        },
                    )
                    retry_task = (
                        f"The previous agent ({role}) failed with error: {e}\n\n"
                        f"Original task: {local_step.description}\n\n"
                        f"Please debug and complete the task."
                    )
                    result = await debugger.think(retry_task)

                    local_step.status = "completed"
                    local_step.result = f"[Retry by debugger] {result}"
                    local_step.completed_at = datetime.utcnow()
                    await step_db.commit()

                    await factory.retire(debugger.id)

                    await self._emit_event(
                        "step_completed",
                        playbook_id=playbook_id,
                        step_id=local_step.id,
                        result_preview=result[:200] if result else "",
                        retried=True,
                    )

                    return result

                except Exception as retry_error:
                    local_step.status = "failed"
                    local_step.result = f"Failed after retry: {retry_error}"
                    local_step.completed_at = datetime.utcnow()
                    await step_db.commit()

                    await self._emit_event(
                        "step_failed",
                        playbook_id=playbook_id,
                        step_id=local_step.id,
                        error=str(retry_error),
                    )

                    raise retry_error

    async def _emit_event(self, event_type: str, **data) -> None:
        """Emit a stream event via the message bus."""
        try:
            await self._bus.publish(
                topic=Topic.STATUS_UPDATE,
                payload={"event_type": event_type, **data},
                sender_id="orchestrator",
            )
        except Exception as e:
            logger.debug("Failed to emit event %s: %s", event_type, e)


# Singleton
orchestrator = Orchestrator()
