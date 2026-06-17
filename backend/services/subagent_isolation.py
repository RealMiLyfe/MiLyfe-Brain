"""Sub-Agent Isolation — Isolated sub-agent execution."""

from typing import Any, Optional

import structlog

logger = structlog.get_logger()


class SubAgentIsolation:
    """Run sub-agents in isolated contexts."""

    async def execute_isolated(
        self,
        role: str,
        task: str,
        context: Optional[str] = None,
        model: Optional[str] = None,
    ) -> str:
        """Execute a sub-agent task in isolation.

        Only the FINAL result returns to the parent.
        All intermediate reasoning/failures/dead-ends discarded.
        """
        from agents.factory import agent_factory

        agent = agent_factory.spawn(role, model=model)
        try:
            result = await agent.think(task, context=context)
            return result.get("response", "")
        finally:
            agent_factory.retire(agent.id)


# Global instance
subagent_isolation = SubAgentIsolation()
