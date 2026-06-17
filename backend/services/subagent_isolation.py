"""MiLyfe Brain — Sub-Agent Context Isolation."""

from __future__ import annotations

from typing import Any, Dict, Optional

import structlog

from models.schemas import AgentRole

logger = structlog.get_logger()


class SubAgentIsolation:
    """Run sub-agents in isolated context (only final result returns)."""

    async def run_isolated(
        self,
        role: AgentRole,
        task: str,
        context: Optional[Dict[str, Any]] = None,
        model: Optional[str] = None,
    ) -> str:
        """Execute a sub-agent in isolation.

        - Sub-agent gets its own message history
        - Only the FINAL result returns to parent
        - All intermediate reasoning/failures/dead-ends discarded
        """
        from agents.factory import agent_factory

        result = await agent_factory.execute_task(
            role=role,
            task=task,
            context=context,
            model_override=model,
        )

        # Return only final output (all intermediate state is in the
        # agent that was spawned and retired by execute_task)
        return result


# Singleton
subagent_isolation = SubAgentIsolation()
