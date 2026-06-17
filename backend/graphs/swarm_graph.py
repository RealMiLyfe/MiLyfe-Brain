"""
MiLyfe Brain - Swarm Graph Patterns

Sub-swarm execution patterns for multi-agent collaboration.
Provides reusable strategies for parallel, sequential, debate,
and map-reduce agent coordination.
"""
from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from agents.factory import AgentFactory
from models.schemas import AgentRole

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Base Class
# ---------------------------------------------------------------------------


class SwarmPattern(ABC):
    """
    Abstract base class for swarm execution patterns.

    All swarm patterns orchestrate multiple agents to collaboratively
    complete a task using different coordination strategies.
    """

    @abstractmethod
    async def execute(self, task: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Execute the swarm pattern on the given task.

        Args:
            task: The task description to execute.
            context: Optional context dict passed to agents.

        Returns:
            The final result string from the swarm execution.
        """
        ...


# ---------------------------------------------------------------------------
# Parallel Swarm
# ---------------------------------------------------------------------------


class ParallelSwarm(SwarmPattern):
    """
    Multiple agents work on the same task concurrently.
    The best result is selected based on the merge strategy.

    Strategies:
      - "best": Use a reviewer agent to pick the best output
      - "longest": Pick the longest response
      - "first": Pick the first successful response
    """

    def __init__(
        self,
        roles: Optional[List[AgentRole]] = None,
        merge_strategy: str = "best",
    ) -> None:
        self.roles: List[AgentRole] = roles or [AgentRole.CODER, AgentRole.CODER, AgentRole.CODER]
        self.merge_strategy: str = merge_strategy

    async def execute(self, task: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Execute all agents in parallel, then merge results."""
        factory = AgentFactory()

        # Run all agents concurrently
        tasks = [
            factory.execute_task(role=role, task=task, context=context)
            for role in self.roles
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out failures
        successful: List[str] = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.warning(
                    "ParallelSwarm agent %s failed: %s",
                    self.roles[i].value,
                    str(result),
                )
            elif isinstance(result, str) and result:
                successful.append(result)

        if not successful:
            return "[ERROR] All parallel agents failed."

        if len(successful) == 1:
            return successful[0]

        # Apply merge strategy
        if self.merge_strategy == "first":
            return successful[0]
        elif self.merge_strategy == "longest":
            return max(successful, key=len)
        elif self.merge_strategy == "best":
            return await self._select_best(task, successful, context)
        else:
            return successful[0]

    async def _select_best(
        self,
        task: str,
        candidates: List[str],
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Use a reviewer agent to select the best result from candidates."""
        factory = AgentFactory()

        numbered = "\n\n".join(
            f"--- Candidate {i + 1} ---\n{c}" for i, c in enumerate(candidates)
        )

        review_task = (
            f"Original task: {task}\n\n"
            f"Multiple agents produced the following solutions:\n\n{numbered}\n\n"
            "Select the best solution. Respond with ONLY the content of the best candidate, "
            "without any commentary or candidate labels."
        )

        try:
            best = await factory.execute_task(
                role=AgentRole.REVIEWER,
                task=review_task,
                context=context,
            )
            return best
        except Exception as e:
            logger.warning("Reviewer selection failed: %s. Using longest.", str(e))
            return max(candidates, key=len)


# ---------------------------------------------------------------------------
# Sequential Swarm
# ---------------------------------------------------------------------------


class SequentialSwarm(SwarmPattern):
    """
    Chain of agents where each builds on the previous agent's output.

    Each agent receives the original task plus the accumulated output
    from all prior agents in the chain.
    """

    def __init__(self, roles: Optional[List[AgentRole]] = None) -> None:
        self.roles: List[AgentRole] = roles or [
            AgentRole.RESEARCHER,
            AgentRole.PLANNER,
            AgentRole.CODER,
        ]

    async def execute(self, task: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Execute agents sequentially, passing output forward."""
        factory = AgentFactory()
        accumulated_output = ""

        for i, role in enumerate(self.roles):
            step_context = dict(context) if context else {}
            step_context["chain_position"] = i + 1
            step_context["total_steps"] = len(self.roles)

            if accumulated_output:
                step_context["prior_output"] = accumulated_output

            step_task = task
            if accumulated_output:
                step_task = (
                    f"Original task: {task}\n\n"
                    f"Previous agent output:\n{accumulated_output}\n\n"
                    f"Build upon the above to continue the task. "
                    f"You are step {i + 1} of {len(self.roles)}."
                )

            try:
                result = await factory.execute_task(
                    role=role,
                    task=step_task,
                    context=step_context,
                )
                accumulated_output = result
            except Exception as e:
                logger.error(
                    "SequentialSwarm agent %s (step %d) failed: %s",
                    role.value,
                    i + 1,
                    str(e),
                )
                # Continue with what we have so far
                if accumulated_output:
                    accumulated_output += f"\n\n[Step {i + 1} ({role.value}) failed: {e}]"
                else:
                    accumulated_output = f"[Step {i + 1} ({role.value}) failed: {e}]"

        return accumulated_output


# ---------------------------------------------------------------------------
# Debate Swarm
# ---------------------------------------------------------------------------


class DebateSwarm(SwarmPattern):
    """
    Adversarial debate pattern: proposer → opponent → improvement → judgment.

    A proposer generates a solution, an opponent critiques it, the proposer
    improves it based on critique, and a judge makes the final assessment.
    Multiple rounds of debate can occur before judgment.
    """

    def __init__(
        self,
        proposer: AgentRole = AgentRole.CODER,
        opponent: AgentRole = AgentRole.REVIEWER,
        judge: AgentRole = AgentRole.PLANNER,
        rounds: int = 2,
    ) -> None:
        self.proposer: AgentRole = proposer
        self.opponent: AgentRole = opponent
        self.judge: AgentRole = judge
        self.rounds: int = max(1, rounds)

    async def execute(self, task: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Execute the debate rounds followed by final judgment."""
        factory = AgentFactory()
        proposal = ""
        critique = ""

        for round_num in range(1, self.rounds + 1):
            # --- Proposer turn ---
            if round_num == 1:
                proposer_task = (
                    f"Task: {task}\n\n"
                    "Provide your best solution to this task."
                )
            else:
                proposer_task = (
                    f"Original task: {task}\n\n"
                    f"Your previous proposal:\n{proposal}\n\n"
                    f"Critique received:\n{critique}\n\n"
                    "Improve your proposal based on the critique. "
                    "Address all valid concerns while maintaining your core approach."
                )

            try:
                proposal = await factory.execute_task(
                    role=self.proposer,
                    task=proposer_task,
                    context=context,
                )
            except Exception as e:
                logger.error("Proposer failed in round %d: %s", round_num, str(e))
                if not proposal:
                    return f"[ERROR] Debate failed: proposer error in round {round_num}: {e}"
                break

            # --- Opponent turn ---
            opponent_task = (
                f"Original task: {task}\n\n"
                f"Proposed solution (round {round_num}):\n{proposal}\n\n"
                "Critically evaluate this proposal. Identify weaknesses, errors, "
                "missing considerations, and potential improvements. "
                "Be specific and constructive."
            )

            try:
                critique = await factory.execute_task(
                    role=self.opponent,
                    task=opponent_task,
                    context=context,
                )
            except Exception as e:
                logger.warning("Opponent failed in round %d: %s", round_num, str(e))
                critique = ""
                break

        # --- Judge turn ---
        judge_task = (
            f"Original task: {task}\n\n"
            f"Final proposal:\n{proposal}\n\n"
        )
        if critique:
            judge_task += f"Final critique:\n{critique}\n\n"

        judge_task += (
            "As the judge, synthesize the best final answer. "
            "Incorporate valid improvements from the critique into the proposal. "
            "Output ONLY the final polished solution."
        )

        try:
            final = await factory.execute_task(
                role=self.judge,
                task=judge_task,
                context=context,
            )
            return final
        except Exception as e:
            logger.warning("Judge failed: %s. Returning last proposal.", str(e))
            return proposal


# ---------------------------------------------------------------------------
# Map-Reduce Swarm
# ---------------------------------------------------------------------------


class MapReduceSwarm(SwarmPattern):
    """
    Map-Reduce pattern: split task into subtasks, execute in parallel, then merge.

    A planner splits the work, worker agents process subtasks concurrently,
    and a reducer agent synthesizes all outputs into a final result.
    """

    def __init__(
        self,
        worker_role: AgentRole = AgentRole.CODER,
        reducer_role: AgentRole = AgentRole.WRITER,
        max_workers: int = 5,
    ) -> None:
        self.worker_role: AgentRole = worker_role
        self.reducer_role: AgentRole = reducer_role
        self.max_workers: int = max_workers

    async def execute(self, task: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Split, map, and reduce the task."""
        factory = AgentFactory()

        # --- Map phase: split the task ---
        split_task = (
            f"Task: {task}\n\n"
            f"Split this task into {self.max_workers} or fewer independent subtasks. "
            "Output ONLY a JSON array of strings, each being a subtask description. "
            "No explanation, no code fences — just the JSON array."
        )

        try:
            split_result = await factory.execute_task(
                role=AgentRole.PLANNER,
                task=split_task,
                context=context,
            )
        except Exception as e:
            logger.error("MapReduce split failed: %s. Executing as single task.", str(e))
            return await factory.execute_task(
                role=self.worker_role,
                task=task,
                context=context,
            )

        # Parse subtasks
        subtasks = self._parse_subtasks(split_result, task)

        # --- Execute subtasks in parallel ---
        worker_tasks = [
            factory.execute_task(
                role=self.worker_role,
                task=subtask,
                context=context,
            )
            for subtask in subtasks
        ]
        worker_results = await asyncio.gather(*worker_tasks, return_exceptions=True)

        # Collect successful results
        outputs: List[str] = []
        for i, result in enumerate(worker_results):
            if isinstance(result, Exception):
                logger.warning(
                    "MapReduce worker %d failed: %s",
                    i + 1,
                    str(result),
                )
                outputs.append(f"[Worker {i + 1} failed: {result}]")
            elif isinstance(result, str):
                outputs.append(result)

        if not outputs:
            return "[ERROR] All map-reduce workers failed."

        # --- Reduce phase: merge outputs ---
        numbered_outputs = "\n\n".join(
            f"--- Subtask {i + 1}: {subtasks[i][:80]} ---\n{output}"
            for i, output in enumerate(outputs)
        )

        reduce_task = (
            f"Original task: {task}\n\n"
            f"The following subtask results need to be synthesized:\n\n"
            f"{numbered_outputs}\n\n"
            "Merge these results into a single coherent final output. "
            "Resolve any conflicts, remove duplicates, and ensure consistency."
        )

        try:
            final = await factory.execute_task(
                role=self.reducer_role,
                task=reduce_task,
                context=context,
            )
            return final
        except Exception as e:
            logger.warning("Reducer failed: %s. Returning concatenated outputs.", str(e))
            return "\n\n".join(outputs)

    def _parse_subtasks(self, split_result: str, original_task: str) -> List[str]:
        """Parse the planner's output into subtask strings."""
        import json

        # Try JSON parsing
        cleaned = split_result.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            lines = [ln for ln in lines if not ln.strip().startswith("```")]
            cleaned = "\n".join(lines).strip()

        try:
            subtasks = json.loads(cleaned)
            if isinstance(subtasks, list) and all(isinstance(s, str) for s in subtasks):
                return subtasks[:self.max_workers]
        except (json.JSONDecodeError, ValueError):
            pass

        # Fallback: try splitting by numbered list
        import re

        numbered = re.findall(r"^\s*\d+[.)]\s+(.+)$", split_result, re.MULTILINE)
        if numbered:
            return numbered[:self.max_workers]

        # Fallback: try bullet list
        bullets = re.findall(r"^\s*[-*]\s+(.+)$", split_result, re.MULTILINE)
        if bullets:
            return bullets[:self.max_workers]

        # Ultimate fallback: use the original task as a single subtask
        return [original_task]


# ---------------------------------------------------------------------------
# Pre-built Configurations
# ---------------------------------------------------------------------------

SWARM_PATTERNS: Dict[str, SwarmPattern] = {
    "parallel_coders": ParallelSwarm(
        roles=[AgentRole.CODER, AgentRole.CODER, AgentRole.CODER],
        merge_strategy="best",
    ),
    "research_then_code": SequentialSwarm(
        roles=[AgentRole.RESEARCHER, AgentRole.PLANNER, AgentRole.CODER],
    ),
    "code_review": SequentialSwarm(
        roles=[AgentRole.CODER, AgentRole.REVIEWER, AgentRole.CODER],
    ),
    "debate": DebateSwarm(
        proposer=AgentRole.CODER,
        opponent=AgentRole.REVIEWER,
        judge=AgentRole.PLANNER,
        rounds=2,
    ),
    "full_pipeline": SequentialSwarm(
        roles=[
            AgentRole.PLANNER,
            AgentRole.RESEARCHER,
            AgentRole.CODER,
            AgentRole.REVIEWER,
            AgentRole.WRITER,
        ],
    ),
}
