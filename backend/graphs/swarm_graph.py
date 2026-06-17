"""MiLyfe Brain — Sub-Swarm Patterns (parallel/sequential/debate)."""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional

import structlog

from agents.factory import agent_factory
from models.schemas import AgentRole

logger = structlog.get_logger()


class SwarmPattern:
    """Base class for swarm execution patterns."""

    async def execute(self, task: str, context: Dict[str, Any] = None) -> str:
        raise NotImplementedError


class ParallelSwarm(SwarmPattern):
    """Multiple agents work on the same task independently."""

    def __init__(self, roles: List[AgentRole], merge_strategy: str = "best"):
        self.roles = roles
        self.merge_strategy = merge_strategy

    async def execute(self, task: str, context: Dict[str, Any] = None) -> str:
        tasks = [
            agent_factory.execute_task(role=role, task=task, context=context)
            for role in self.roles
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        valid = [r for r in results if isinstance(r, str) and r]
        if not valid:
            return "All agents failed"

        if self.merge_strategy == "best":
            return max(valid, key=len)
        elif self.merge_strategy == "concat":
            return "\n\n---\n\n".join(valid)
        elif self.merge_strategy == "vote":
            return valid[0]  # Simplified
        return valid[0]


class SequentialSwarm(SwarmPattern):
    """Agents work in sequence, each building on prior."""

    def __init__(self, roles: List[AgentRole]):
        self.roles = roles

    async def execute(self, task: str, context: Dict[str, Any] = None) -> str:
        context = context or {}
        result = ""
        for role in self.roles:
            augmented = f"{task}\n\nPrevious work:\n{result}" if result else task
            result = await agent_factory.execute_task(
                role=role, task=augmented, context=context
            )
        return result



class DebateSwarm(SwarmPattern):
    """Two agents debate, a third judges the outcome."""

    def __init__(
        self,
        proposer: AgentRole = AgentRole.CODER,
        opponent: AgentRole = AgentRole.CRITIC,
        judge: AgentRole = AgentRole.ORCHESTRATOR,
        rounds: int = 2,
    ):
        self.proposer = proposer
        self.opponent = opponent
        self.judge = judge
        self.rounds = rounds

    async def execute(self, task: str, context: Dict[str, Any] = None) -> str:
        context = context or {}

        # Initial proposal
        proposal = await agent_factory.execute_task(
            role=self.proposer, task=task, context=context
        )

        # Debate rounds
        for round_num in range(self.rounds):
            # Opponent critiques
            critique_task = f"""Review this proposal and identify issues:

Task: {task}
Proposal: {proposal}

Be specific about problems and suggest improvements."""

            critique = await agent_factory.execute_task(
                role=self.opponent, task=critique_task, context=context
            )

            # Proposer responds
            response_task = f"""Address this critique and improve your work:

Original task: {task}
Your proposal: {proposal}
Critique: {critique}

Provide an improved version."""

            proposal = await agent_factory.execute_task(
                role=self.proposer, task=response_task, context=context
            )

        # Judge makes final call
        judge_task = f"""Evaluate this final result:

Task: {task}
Final proposal: {proposal}

Is this acceptable? Output the final approved version."""

        final = await agent_factory.execute_task(
            role=self.judge, task=judge_task, context=context
        )

        return final


class MapReduceSwarm(SwarmPattern):
    """Split task into parts, process in parallel, merge results."""

    def __init__(
        self,
        worker_role: AgentRole = AgentRole.CODER,
        reducer_role: AgentRole = AgentRole.ORCHESTRATOR,
    ):
        self.worker_role = worker_role
        self.reducer_role = reducer_role

    async def execute(
        self,
        task: str,
        subtasks: List[str] = None,
        context: Dict[str, Any] = None,
    ) -> str:
        context = context or {}

        if not subtasks:
            # Ask planner to split the task
            split_result = await agent_factory.execute_task(
                role=AgentRole.PLANNER,
                task=f"Split this into 2-5 independent subtasks:\n{task}",
                context=context,
            )
            subtasks = [line.strip() for line in split_result.split("\n") if line.strip()]

        # Map: execute all subtasks in parallel
        tasks = [
            agent_factory.execute_task(
                role=self.worker_role, task=st, context=context
            )
            for st in subtasks
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Reduce: merge results
        valid_results = [
            f"Subtask: {subtasks[i]}\nResult: {r}"
            for i, r in enumerate(results)
            if isinstance(r, str)
        ]

        reduce_task = f"""Merge these results into a coherent whole:

Original task: {task}

Results:
{chr(10).join(valid_results)}

Produce the final merged output."""

        return await agent_factory.execute_task(
            role=self.reducer_role, task=reduce_task, context=context
        )


# Pre-built swarm configurations
SWARM_PATTERNS = {
    "parallel_coders": ParallelSwarm(
        roles=[AgentRole.CODER, AgentRole.CODER, AgentRole.CODER],
        merge_strategy="best",
    ),
    "research_then_code": SequentialSwarm(
        roles=[AgentRole.RESEARCHER, AgentRole.PLANNER, AgentRole.CODER],
    ),
    "code_review": SequentialSwarm(
        roles=[AgentRole.CODER, AgentRole.CRITIC, AgentRole.CODER],
    ),
    "design_implement_review": SequentialSwarm(
        roles=[AgentRole.DESIGNER, AgentRole.CODER, AgentRole.CRITIC],
    ),
    "debate": DebateSwarm(),
    "full_pipeline": SequentialSwarm(
        roles=[
            AgentRole.PLANNER,
            AgentRole.RESEARCHER,
            AgentRole.CODER,
            AgentRole.CRITIC,
            AgentRole.WRITER,
        ],
    ),
}
