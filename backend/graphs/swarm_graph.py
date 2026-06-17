"""Swarm Graph — Sub-swarm patterns for complex multi-agent workflows.

Supports: parallel execution, sequential chains, debate/consensus patterns.
"""

import asyncio
from typing import Any, Optional

import structlog

from agents.factory import agent_factory
from agents.message_bus import message_bus

logger = structlog.get_logger()


class SwarmPattern:
    """Base class for swarm execution patterns."""

    async def execute(self, task: str, context: Optional[str] = None) -> dict:
        raise NotImplementedError


class ParallelSwarm(SwarmPattern):
    """Execute multiple agents in parallel on the same or different tasks."""

    def __init__(self, roles: list[str], model: Optional[str] = None):
        self.roles = roles
        self.model = model

    async def execute(self, task: str, context: Optional[str] = None) -> dict:
        """Run agents in parallel, collect all results."""
        agents = [agent_factory.spawn(role, model=self.model) for role in self.roles]

        tasks = [agent.think(task, context=context) for agent in agents]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        outputs = []
        for agent, result in zip(agents, results):
            if isinstance(result, Exception):
                outputs.append({"role": agent.role, "error": str(result)})
            else:
                outputs.append({"role": agent.role, "response": result.get("response", "")})

            agent_factory.retire(agent.id)

        return {"pattern": "parallel", "results": outputs}


class SequentialSwarm(SwarmPattern):
    """Execute agents sequentially, passing output to next agent."""

    def __init__(self, roles: list[str], model: Optional[str] = None):
        self.roles = roles
        self.model = model

    async def execute(self, task: str, context: Optional[str] = None) -> dict:
        """Run agents sequentially, each building on the previous result."""
        accumulated_context = context or ""
        results = []

        for role in self.roles:
            agent = agent_factory.spawn(role, model=self.model)

            full_task = task if not accumulated_context else f"{task}\n\nPrevious work:\n{accumulated_context}"
            result = await agent.think(full_task)

            response = result.get("response", "")
            results.append({"role": role, "response": response})
            accumulated_context += f"\n\n[{role}]: {response}"

            agent_factory.retire(agent.id)

        return {"pattern": "sequential", "results": results, "final": results[-1] if results else None}


class DebateSwarm(SwarmPattern):
    """Multiple agents debate a topic, then a judge synthesizes."""

    def __init__(self, debater_roles: list[str] = None, rounds: int = 2, model: Optional[str] = None):
        self.debater_roles = debater_roles or ["researcher", "coder", "critic"]
        self.rounds = rounds
        self.model = model

    async def execute(self, task: str, context: Optional[str] = None) -> dict:
        """Run debate rounds then synthesize with orchestrator."""
        debate_history = []

        for round_num in range(self.rounds):
            round_results = []
            for role in self.debater_roles:
                agent = agent_factory.spawn(role, model=self.model)

                debate_context = f"Round {round_num + 1} of debate.\n"
                if debate_history:
                    debate_context += "Previous arguments:\n"
                    for entry in debate_history[-len(self.debater_roles):]:
                        debate_context += f"- [{entry['role']}]: {entry['response'][:200]}\n"

                result = await agent.think(
                    f"{task}\n\n{debate_context}\n\nProvide your perspective and argument.",
                    context=context,
                )
                response = result.get("response", "")
                round_results.append({"role": role, "response": response, "round": round_num + 1})
                debate_history.append({"role": role, "response": response})

                agent_factory.retire(agent.id)

        # Synthesize with orchestrator
        judge = agent_factory.spawn("orchestrator", model=self.model)
        synthesis_context = "Debate results:\n" + "\n".join(
            f"[{e['role']}]: {e['response'][:300]}" for e in debate_history
        )
        synthesis = await judge.think(
            f"Synthesize the following debate into a final decision:\n\n{synthesis_context}",
        )
        agent_factory.retire(judge.id)

        return {
            "pattern": "debate",
            "rounds": debate_history,
            "synthesis": synthesis.get("response", ""),
        }


class SwarmGraph:
    """Factory for creating and executing swarm patterns."""

    @staticmethod
    def parallel(roles: list[str], **kwargs) -> ParallelSwarm:
        return ParallelSwarm(roles, **kwargs)

    @staticmethod
    def sequential(roles: list[str], **kwargs) -> SequentialSwarm:
        return SequentialSwarm(roles, **kwargs)

    @staticmethod
    def debate(debater_roles: list[str] = None, **kwargs) -> DebateSwarm:
        return DebateSwarm(debater_roles, **kwargs)

    @staticmethod
    async def execute_pattern(pattern: str, task: str, roles: list[str] = None, **kwargs) -> dict:
        """Execute a named swarm pattern."""
        roles = roles or ["researcher", "coder", "critic"]

        if pattern == "parallel":
            swarm = ParallelSwarm(roles, **kwargs)
        elif pattern == "sequential":
            swarm = SequentialSwarm(roles, **kwargs)
        elif pattern == "debate":
            swarm = DebateSwarm(roles, **kwargs)
        else:
            raise ValueError(f"Unknown swarm pattern: {pattern}")

        return await swarm.execute(task)


# Global instance
swarm_graph = SwarmGraph()
