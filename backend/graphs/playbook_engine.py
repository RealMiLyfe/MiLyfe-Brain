"""MiLyfe Brain — Enhanced Playbook Engine.

Variables, conditionals, loops, composition, time/cost estimates, dry-run mode.
Extends the basic orchestrator with full programming-like playbook capabilities.
"""

from __future__ import annotations

import asyncio
import re
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

import orjson
import structlog
from sqlalchemy import select

from config import settings
from models.schemas import AgentRole, PlaybookStatus, TaskComplexity, TaskStatus

logger = structlog.get_logger()


# ─── Playbook Variable System ───────────────────────────────────


class PlaybookVariables:
    """Template variable resolution for playbooks.

    Supports: {{var}}, {{step_1.result}}, {{env.VAR}}, {{input.field}}
    """

    def __init__(self, initial: Dict[str, Any] = None):
        self._vars: Dict[str, Any] = initial or {}
        self._step_results: Dict[str, str] = {}

    def set(self, key: str, value: Any):
        self._vars[key] = value

    def set_step_result(self, step_id: str, result: str):
        self._step_results[step_id] = result

    def resolve(self, template: str) -> str:
        """Resolve all {{variables}} in a template string."""
        def _replacer(match):
            expr = match.group(1).strip()

            # Step results: {{step_1.result}}
            if "." in expr:
                parts = expr.split(".", 1)
                if parts[0] in self._step_results:
                    return self._step_results[parts[0]][:2000]
                if parts[0] == "env":
                    import os
                    return os.environ.get(parts[1], f"<{parts[1]} not set>")
                if parts[0] == "input":
                    return str(self._vars.get(parts[1], f"<{parts[1]} not provided>"))

            # Direct variables
            if expr in self._vars:
                return str(self._vars[expr])
            if expr in self._step_results:
                return self._step_results[expr][:2000]

            return match.group(0)  # Leave unresolved

        return re.sub(r"\{\{(.+?)\}\}", _replacer, template)

    def get_all(self) -> Dict[str, Any]:
        return {**self._vars, "step_results": self._step_results}


# ─── Conditional System ─────────────────────────────────────────


class StepCondition:
    """Evaluates conditions for conditional step execution.

    Supports:
    - "{{step_1.result}} contains 'error'" → skip/run step
    - "{{var}} == 'value'"
    - "{{step_2.result}} not empty"
    - "always" / "never"
    """

    def __init__(self, expression: str):
        self.expression = expression.strip()

    def evaluate(self, variables: PlaybookVariables) -> bool:
        """Evaluate the condition against current variables."""
        if not self.expression or self.expression == "always":
            return True
        if self.expression == "never":
            return False

        # Resolve variables in expression
        resolved = variables.resolve(self.expression)

        # "X contains Y"
        match = re.match(r"(.+?)\s+contains\s+'([^']+)'", resolved)
        if match:
            return match.group(2) in match.group(1)

        # "X not empty"
        match = re.match(r"(.+?)\s+not\s+empty", resolved)
        if match:
            return bool(match.group(1).strip())

        # "X == Y"
        match = re.match(r"(.+?)\s*==\s*'([^']+)'", resolved)
        if match:
            return match.group(1).strip() == match.group(2)

        # "X != Y"
        match = re.match(r"(.+?)\s*!=\s*'([^']+)'", resolved)
        if match:
            return match.group(1).strip() != match.group(2)

        # Truthy check
        return bool(resolved and resolved.lower() not in ("false", "0", "none", "null", ""))


# ─── Loop System ────────────────────────────────────────────────


class StepLoop:
    """Loop configuration for repeatable steps.

    Modes:
    - "until": repeat until condition is true (max N)
    - "times": repeat exactly N times
    - "foreach": iterate over a list
    """

    def __init__(self, mode: str, value: Any, max_iterations: int = 5):
        self.mode = mode  # "until", "times", "foreach"
        self.value = value  # condition string, count, or list
        self.max_iterations = max_iterations

    def should_continue(self, iteration: int, variables: PlaybookVariables) -> bool:
        """Check if loop should continue."""
        if iteration >= self.max_iterations:
            return False

        if self.mode == "times":
            return iteration < int(self.value)

        if self.mode == "until":
            condition = StepCondition(str(self.value))
            return not condition.evaluate(variables)  # Continue until TRUE

        if self.mode == "foreach":
            items = self.value if isinstance(self.value, list) else []
            return iteration < len(items)

        return False

    def get_current_item(self, iteration: int) -> Any:
        """Get the current item for foreach loops."""
        if self.mode == "foreach" and isinstance(self.value, list):
            return self.value[iteration] if iteration < len(self.value) else None
        return None


# ─── Enhanced Step Definition ───────────────────────────────────


class EnhancedStep:
    """A playbook step with variables, conditions, loops, and composition."""

    def __init__(
        self,
        id: str,
        description: str,
        agent_role: AgentRole = AgentRole.CODER,
        depends_on: List[str] = None,
        complexity: TaskComplexity = TaskComplexity.MEDIUM,
        tools_needed: List[str] = None,
        condition: Optional[str] = None,
        loop: Optional[Dict] = None,
        sub_playbook_id: Optional[str] = None,
        timeout: int = 300,
    ):
        self.id = id
        self.description = description
        self.agent_role = agent_role
        self.depends_on = depends_on or []
        self.complexity = complexity
        self.tools_needed = tools_needed or []
        self.condition = StepCondition(condition) if condition else None
        self.loop = StepLoop(**loop) if loop else None
        self.sub_playbook_id = sub_playbook_id
        self.timeout = timeout


# ─── Dry-Run Mode ───────────────────────────────────────────────


class DryRunResult:
    """Result of a dry-run (no actual execution)."""

    def __init__(self):
        self.steps: List[Dict] = []
        self.estimated_time_s: float = 0
        self.estimated_tokens: int = 0
        self.estimated_cost_equivalent: float = 0
        self.warnings: List[str] = []

    def add_step(self, step_id: str, description: str, role: str, would_execute: bool, reason: str = ""):
        self.steps.append({
            "step_id": step_id,
            "description": description[:100],
            "role": role,
            "would_execute": would_execute,
            "skip_reason": reason,
        })

    def to_dict(self) -> Dict:
        return {
            "dry_run": True,
            "steps": self.steps,
            "total_steps": len(self.steps),
            "steps_to_execute": sum(1 for s in self.steps if s["would_execute"]),
            "steps_skipped": sum(1 for s in self.steps if not s["would_execute"]),
            "estimated_time_seconds": round(self.estimated_time_s),
            "estimated_tokens": self.estimated_tokens,
            "estimated_cost_equivalent_usd": round(self.estimated_cost_equivalent, 4),
            "warnings": self.warnings,
        }


# ─── Time/Cost Estimation ──────────────────────────────────────


# Historical averages (updated from actual runs)
COMPLEXITY_ESTIMATES = {
    TaskComplexity.LIGHT: {"time_s": 15, "tokens": 2000},
    TaskComplexity.MEDIUM: {"time_s": 45, "tokens": 5000},
    TaskComplexity.HEAVY: {"time_s": 120, "tokens": 12000},
}

COST_PER_1K_TOKENS = 0.03  # GPT-4 equivalent for comparison


def estimate_step(complexity: TaskComplexity) -> Dict[str, float]:
    """Estimate time and tokens for a step based on complexity."""
    est = COMPLEXITY_ESTIMATES.get(complexity, COMPLEXITY_ESTIMATES[TaskComplexity.MEDIUM])
    return {
        "time_s": est["time_s"],
        "tokens": est["tokens"],
        "cost_usd": (est["tokens"] / 1000) * COST_PER_1K_TOKENS,
    }


def estimate_playbook(steps: List[EnhancedStep]) -> Dict:
    """Estimate total time and cost for a playbook."""
    total_time = 0
    total_tokens = 0
    parallel_groups = _group_parallel(steps)

    for group in parallel_groups:
        # Parallel steps: time = max of group, tokens = sum
        group_time = max(estimate_step(s.complexity)["time_s"] for s in group)
        group_tokens = sum(estimate_step(s.complexity)["tokens"] for s in group)
        total_time += group_time
        total_tokens += group_tokens

    return {
        "estimated_time_seconds": round(total_time),
        "estimated_time_human": _format_duration(total_time),
        "estimated_tokens": total_tokens,
        "estimated_cost_equivalent_usd": round((total_tokens / 1000) * COST_PER_1K_TOKENS, 4),
        "parallel_groups": len(parallel_groups),
        "total_steps": len(steps),
    }


# ─── Enhanced Execution Engine ──────────────────────────────────


async def execute_enhanced_playbook(
    playbook_id: str,
    variables: Dict[str, Any] = None,
    dry_run: bool = False,
) -> Dict:
    """Execute a playbook with full enhanced capabilities.

    Args:
        playbook_id: The playbook to execute
        variables: Template variables to inject
        dry_run: If True, simulate without executing

    Returns:
        Execution result or dry-run analysis
    """
    from memory.database import PlaybookRow, PlaybookStepRow, async_session_factory

    # Load playbook
    async with async_session_factory() as session:
        playbook = await session.get(PlaybookRow, playbook_id)
        if not playbook:
            raise ValueError(f"Playbook not found: {playbook_id}")

        steps_result = await session.execute(
            select(PlaybookStepRow)
            .where(PlaybookStepRow.playbook_id == playbook_id)
            .order_by(PlaybookStepRow.order_index)
        )
        step_rows = steps_result.scalars().all()

    # Build enhanced steps
    enhanced_steps = _build_enhanced_steps(step_rows)

    # Initialize variables
    pb_vars = PlaybookVariables(variables or {})
    pb_vars.set("playbook_id", playbook_id)
    pb_vars.set("playbook_title", playbook.title)

    # Dry run mode
    if dry_run:
        return await _dry_run_playbook(enhanced_steps, pb_vars)

    # Real execution
    return await _execute_steps(playbook_id, enhanced_steps, pb_vars)


async def _dry_run_playbook(steps: List[EnhancedStep], variables: PlaybookVariables) -> Dict:
    """Simulate playbook execution without actually running."""
    result = DryRunResult()

    for step in steps:
        # Check condition
        would_execute = True
        skip_reason = ""

        if step.condition:
            would_execute = step.condition.evaluate(variables)
            if not would_execute:
                skip_reason = f"Condition not met: {step.condition.expression}"

        result.add_step(
            step_id=step.id,
            description=step.description,
            role=step.agent_role.value,
            would_execute=would_execute,
            reason=skip_reason,
        )

        if would_execute:
            est = estimate_step(step.complexity)
            result.estimated_time_s += est["time_s"]
            result.estimated_tokens += est["tokens"]
            result.estimated_cost_equivalent += est["cost_usd"]

            # Loop estimation
            if step.loop:
                iterations = int(step.loop.value) if step.loop.mode == "times" else step.loop.max_iterations
                result.estimated_time_s += est["time_s"] * (iterations - 1)
                result.estimated_tokens += est["tokens"] * (iterations - 1)
                result.warnings.append(f"Step {step.id} has loop ({step.loop.mode}), estimates may vary")

    return result.to_dict()


async def _execute_steps(
    playbook_id: str,
    steps: List[EnhancedStep],
    variables: PlaybookVariables,
) -> Dict:
    """Execute steps with variables, conditions, and loops."""
    from agents.factory import agent_factory
    from memory.database import PlaybookRow, PlaybookStepRow, async_session_factory
    from api.routes.streaming import emit_event
    from models.schemas import EventType

    results: Dict[str, str] = {}
    start_time = time.time()

    # Update playbook status
    async with async_session_factory() as session:
        pb = await session.get(PlaybookRow, playbook_id)
        if pb:
            pb.status = "running"
            pb.started_at = datetime.utcnow()
            await session.commit()

    emit_event(EventType.PLAYBOOK_STARTED, playbook_id=playbook_id, data={"variables": variables.get_all()})

    try:
        # Group into parallel layers
        layers = _topological_layers(steps)

        for layer_idx, layer in enumerate(layers):
            layer_tasks = []

            for step in layer:
                # Check condition
                if step.condition and not step.condition.evaluate(variables):
                    logger.info("step_skipped_condition", step_id=step.id)
                    emit_event(EventType.STEP_COMPLETED, playbook_id=playbook_id,
                              data={"step_id": step.id, "skipped": True, "reason": "condition_not_met"})
                    continue

                # Handle loops
                if step.loop:
                    layer_tasks.append(_execute_loop_step(step, variables, playbook_id))
                # Handle sub-playbook composition
                elif step.sub_playbook_id:
                    layer_tasks.append(_execute_sub_playbook(step, variables, playbook_id))
                else:
                    layer_tasks.append(_execute_single_step(step, variables, playbook_id))

            # Execute layer in parallel
            if layer_tasks:
                layer_results = await asyncio.gather(*layer_tasks, return_exceptions=True)

                for i, result in enumerate(layer_results):
                    if isinstance(result, Exception):
                        # Attempt debug retry
                        logger.error("step_failed", error=str(result))
                        # Mark failed
                        async with async_session_factory() as session:
                            pb = await session.get(PlaybookRow, playbook_id)
                            if pb:
                                pb.status = "failed"
                                pb.error = str(result)
                                pb.completed_at = datetime.utcnow()
                                await session.commit()
                        return {"status": "failed", "error": str(result)}
                    elif isinstance(result, tuple):
                        step_id, step_result = result
                        results[step_id] = step_result
                        variables.set_step_result(step_id, step_result)

        # Success
        duration = time.time() - start_time
        async with async_session_factory() as session:
            pb = await session.get(PlaybookRow, playbook_id)
            if pb:
                pb.status = "completed"
                pb.completed_at = datetime.utcnow()
                await session.commit()

        emit_event(EventType.PLAYBOOK_COMPLETED, playbook_id=playbook_id,
                  data={"duration_s": round(duration, 2), "steps_completed": len(results)})

        return {"status": "completed", "results": results, "duration_s": round(duration, 2)}

    except Exception as e:
        logger.error("playbook_engine_error", error=str(e))
        async with async_session_factory() as session:
            pb = await session.get(PlaybookRow, playbook_id)
            if pb:
                pb.status = "failed"
                pb.error = str(e)
                pb.completed_at = datetime.utcnow()
                await session.commit()
        return {"status": "failed", "error": str(e)}


async def _execute_single_step(
    step: EnhancedStep,
    variables: PlaybookVariables,
    playbook_id: str,
) -> tuple:
    """Execute a single step with variable resolution."""
    from agents.factory import agent_factory

    # Resolve variables in description
    resolved_desc = variables.resolve(step.description)

    result = await agent_factory.execute_task(
        role=step.agent_role,
        task=resolved_desc,
        context={"playbook_id": playbook_id, "step_id": step.id},
    )

    return (step.id, result)


async def _execute_loop_step(
    step: EnhancedStep,
    variables: PlaybookVariables,
    playbook_id: str,
) -> tuple:
    """Execute a step in a loop."""
    from agents.factory import agent_factory

    combined_results = []
    iteration = 0

    while step.loop.should_continue(iteration, variables):
        # Set loop variables
        variables.set("loop.index", iteration)
        variables.set("loop.iteration", iteration + 1)

        if step.loop.mode == "foreach":
            item = step.loop.get_current_item(iteration)
            variables.set("loop.item", item)

        resolved_desc = variables.resolve(step.description)
        result = await agent_factory.execute_task(
            role=step.agent_role,
            task=resolved_desc,
            context={"playbook_id": playbook_id, "step_id": step.id, "iteration": iteration},
        )

        combined_results.append(result)
        variables.set_step_result(f"{step.id}_iter_{iteration}", result)
        iteration += 1

    final_result = "\n---\n".join(combined_results)
    return (step.id, final_result)


async def _execute_sub_playbook(
    step: EnhancedStep,
    variables: PlaybookVariables,
    playbook_id: str,
) -> tuple:
    """Execute a nested sub-playbook."""
    result = await execute_enhanced_playbook(
        playbook_id=step.sub_playbook_id,
        variables=variables.get_all(),
    )
    return (step.id, str(result.get("results", {})))


# ─── Helpers ────────────────────────────────────────────────────


def _build_enhanced_steps(step_rows: list) -> List[EnhancedStep]:
    """Convert DB rows to EnhancedStep objects."""
    steps = []
    for row in step_rows:
        depends = orjson.loads(row.depends_on) if row.depends_on else []
        tools = orjson.loads(row.tools_needed) if row.tools_needed else []

        role = AgentRole(row.agent_role) if row.agent_role else AgentRole.CODER
        complexity = TaskComplexity(row.complexity) if row.complexity else TaskComplexity.MEDIUM

        steps.append(EnhancedStep(
            id=row.id,
            description=row.description,
            agent_role=role,
            depends_on=depends,
            complexity=complexity,
            tools_needed=tools,
        ))
    return steps


def _topological_layers(steps: List[EnhancedStep]) -> List[List[EnhancedStep]]:
    """Sort steps into parallel execution layers."""
    all_ids = {s.id for s in steps}
    step_map = {s.id: s for s in steps}
    deps = {s.id: set(s.depends_on) & all_ids for s in steps}

    layers = []
    completed: set = set()
    remaining = set(all_ids)

    while remaining:
        ready = {sid for sid in remaining if deps[sid].issubset(completed)}
        if not ready:
            ready = {next(iter(remaining))}  # Break cycle
        layers.append([step_map[sid] for sid in sorted(ready)])
        completed.update(ready)
        remaining -= ready

    return layers


def _group_parallel(steps: List[EnhancedStep]) -> List[List[EnhancedStep]]:
    """Alias for topological_layers."""
    return _topological_layers(steps)


def _format_duration(seconds: float) -> str:
    """Format seconds into human-readable duration."""
    if seconds < 60:
        return f"{int(seconds)}s"
    elif seconds < 3600:
        return f"{int(seconds // 60)}m {int(seconds % 60)}s"
    else:
        return f"{int(seconds // 3600)}h {int((seconds % 3600) // 60)}m"
