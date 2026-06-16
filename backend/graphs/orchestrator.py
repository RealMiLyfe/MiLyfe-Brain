"""Orchestrator — Step executor with parallel execution, retry, and debug.

Executes parsed playbook steps using the agent swarm.
"""

import asyncio
import uuid
from datetime import datetime
from typing import Optional

import structlog

from agents.factory import agent_factory
from agents.message_bus import message_bus
from config import settings

logger = structlog.get_logger()


class Orchestrator:
    """Execute playbook steps with dependency resolution and parallel execution."""

    async def execute_playbook(self, playbook_id: str) -> dict:
        """Execute a complete playbook.

        1. Load steps from database
        2. Topological sort by dependencies
        3. Group into parallel layers
        4. Execute each layer (parallel within, sequential across)
        5. Handle failures with retry + debugger agent
        """
        from memory.database import db
        from api.routes.streaming import broadcast_event

        # Update playbook status
        await db.execute(
            "UPDATE playbooks SET status = 'running' WHERE id = ?", (playbook_id,)
        )

        await broadcast_event("playbook_started", {"playbook_id": playbook_id})

        try:
            # Load steps
            steps = await db.fetch_all(
                "SELECT * FROM playbook_steps WHERE playbook_id = ? ORDER BY rowid",
                (playbook_id,),
            )

            if not steps:
                # Parse from raw_text if no steps exist
                playbook = await db.fetch_one(
                    "SELECT * FROM playbooks WHERE id = ?", (playbook_id,)
                )
                if playbook and (playbook.get("raw_text") or playbook.get("description")):
                    from graphs.playbook_parser import playbook_parser
                    raw = playbook.get("raw_text") or playbook["description"]
                    parsed_steps = await playbook_parser.parse(raw)

                    # Store parsed steps
                    for step_data in parsed_steps:
                        step_id = step_data.get("id", str(uuid.uuid4()))
                        await db.execute(
                            """INSERT INTO playbook_steps
                               (id, playbook_id, description, agent_role, status, started_at)
                               VALUES (?, ?, ?, ?, ?, ?)""",
                            (step_id, playbook_id, step_data["description"],
                             step_data.get("agent_role", "coder"), "pending", None),
                        )

                    steps = await db.fetch_all(
                        "SELECT * FROM playbook_steps WHERE playbook_id = ? ORDER BY rowid",
                        (playbook_id,),
                    )

            if not steps:
                raise ValueError("No steps to execute")

            # Group into execution layers (simplified: sequential for now)
            layers = self._build_execution_layers(steps)

            # Execute layers
            for layer_idx, layer in enumerate(layers):
                await broadcast_event(
                    "layer_started",
                    {"playbook_id": playbook_id, "layer": layer_idx, "step_count": len(layer)},
                )

                # Execute steps in parallel within layer
                tasks = [self._execute_step(step, playbook_id) for step in layer]
                results = await asyncio.gather(*tasks, return_exceptions=True)

                # Check for failures
                for step, result in zip(layer, results):
                    if isinstance(result, Exception):
                        # Try retry with debugger
                        retry_success = await self._retry_with_debugger(step, playbook_id, str(result))
                        if not retry_success:
                            await db.execute(
                                "UPDATE playbook_steps SET status = 'failed', result = ? WHERE id = ?",
                                (str(result), step["id"]),
                            )

            # Mark playbook completed
            now = datetime.utcnow().isoformat()
            failed_steps = await db.fetch_all(
                "SELECT * FROM playbook_steps WHERE playbook_id = ? AND status = 'failed'",
                (playbook_id,),
            )

            if failed_steps:
                await db.execute(
                    "UPDATE playbooks SET status = 'failed', error = ?, completed_at = ? WHERE id = ?",
                    (f"{len(failed_steps)} step(s) failed", now, playbook_id),
                )
            else:
                await db.execute(
                    "UPDATE playbooks SET status = 'completed', completed_at = ? WHERE id = ?",
                    (now, playbook_id),
                )

            await broadcast_event("playbook_completed", {"playbook_id": playbook_id})
            return {"status": "completed", "playbook_id": playbook_id}

        except Exception as e:
            logger.error("Playbook execution failed", playbook_id=playbook_id, error=str(e))
            now = datetime.utcnow().isoformat()
            await db.execute(
                "UPDATE playbooks SET status = 'failed', error = ?, completed_at = ? WHERE id = ?",
                (str(e), now, playbook_id),
            )
            await broadcast_event("playbook_failed", {"playbook_id": playbook_id, "error": str(e)})
            return {"status": "failed", "playbook_id": playbook_id, "error": str(e)}

    async def _execute_step(self, step: dict, playbook_id: str) -> str:
        """Execute a single step using the appropriate agent."""
        from memory.database import db
        from api.routes.streaming import broadcast_event

        step_id = step["id"]
        role = step.get("agent_role", "coder")
        description = step["description"]

        # Mark step as running
        now = datetime.utcnow().isoformat()
        await db.execute(
            "UPDATE playbook_steps SET status = 'running', started_at = ? WHERE id = ?",
            (now, step_id),
        )

        await broadcast_event(
            "step_started",
            {"playbook_id": playbook_id, "step_id": step_id, "role": role},
            agent_role=role,
        )

        # Spawn or reuse agent
        agent = agent_factory.spawn_or_get(role)

        await broadcast_event(
            "agent_spawned",
            {"agent_id": agent.id, "role": role, "name": agent.name},
            agent_id=agent.id,
            agent_role=role,
        )

        # Execute
        result = await agent.think(description)
        response = result.get("response", "")

        # Mark completed
        completed_at = datetime.utcnow().isoformat()
        await db.execute(
            "UPDATE playbook_steps SET status = 'completed', result = ?, completed_at = ? WHERE id = ?",
            (response[:5000], completed_at, step_id),
        )

        # Log action
        log_id = str(uuid.uuid4())
        await db.execute(
            """INSERT INTO action_logs (id, playbook_id, agent_id, agent_role, action_type, description, result, timestamp)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (log_id, playbook_id, agent.id, role, "llm_call", description[:500], response[:1000], completed_at),
        )

        await broadcast_event(
            "step_completed",
            {"playbook_id": playbook_id, "step_id": step_id, "response": response[:200]},
            agent_id=agent.id,
            agent_role=role,
        )

        return response

    async def _retry_with_debugger(self, step: dict, playbook_id: str, error: str) -> bool:
        """Retry a failed step using the debugger agent."""
        from api.routes.streaming import broadcast_event

        logger.info("Retrying step with debugger", step_id=step["id"], error=error[:100])

        await broadcast_event(
            "step_retry",
            {"playbook_id": playbook_id, "step_id": step["id"], "error": error[:200]},
        )

        try:
            debugger = agent_factory.spawn_or_get("debugger")
            debug_result = await debugger.think(
                f"A step failed with error: {error}\n\nOriginal task: {step['description']}\n\n"
                f"Please diagnose the issue and suggest a fix."
            )

            fix = debug_result.get("response", "")
            if fix and "cannot" not in fix.lower():
                # Try re-executing with the fix context
                agent = agent_factory.spawn_or_get(step.get("agent_role", "coder"))
                retry_result = await agent.think(
                    f"{step['description']}\n\nPrevious attempt failed: {error}\nSuggested fix: {fix}"
                )
                if retry_result.get("error") is None:
                    from memory.database import db
                    await db.execute(
                        "UPDATE playbook_steps SET status = 'completed', result = ? WHERE id = ?",
                        (retry_result.get("response", "")[:5000], step["id"]),
                    )
                    return True
        except Exception as e:
            logger.error("Retry with debugger failed", error=str(e))

        return False

    def _build_execution_layers(self, steps: list[dict]) -> list[list[dict]]:
        """Group steps into parallel execution layers based on dependencies.

        Steps with no unresolved dependencies go in the same layer.
        """
        remaining = list(steps)
        completed_ids: set[str] = set()
        layers: list[list[dict]] = []

        max_iterations = len(steps) + 1
        iteration = 0

        while remaining and iteration < max_iterations:
            iteration += 1
            current_layer = []

            for step in remaining:
                # For simplicity, treat steps as sequential if no dependency info
                deps = []  # Steps table doesn't store depends_on currently
                if all(dep in completed_ids for dep in deps):
                    current_layer.append(step)

            if not current_layer:
                # No progress possible — add all remaining as a layer
                current_layer = remaining[:]

            layers.append(current_layer)
            for step in current_layer:
                completed_ids.add(step["id"])
                remaining.remove(step)

        return layers


# Global instance
orchestrator = Orchestrator()
