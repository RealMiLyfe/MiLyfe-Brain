"""Agent factory for spawning, tracking, and managing agent instances.

Provides lifecycle management for the agent swarm.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Callable, Coroutine, Dict, List, Optional

from config import settings
from agents.base import AgentRole, AgentState, AgentStatus, BaseAgent
from agents.message_bus import Topic, get_message_bus
from agents.roles import ROLE_TO_CLASS

logger = logging.getLogger(__name__)


class AgentFactory:
    """Factory for creating and managing agent instances.

    Handles:
    - Spawning agents by role with appropriate configuration
    - Tracking active agents and their states
    - Retiring agents and cleaning up resources
    - Direct chat without playbook (tool-assisted conversation)
    """

    def __init__(
        self,
        tool_executor: Optional[Callable[..., Coroutine[Any, Any, str]]] = None,
        max_agents: int = settings.max_agents,
    ) -> None:
        """Initialize the agent factory.

        Args:
            tool_executor: Optional async callable(name, arguments) -> str
                          that handles tool execution for all agents.
            max_agents: Maximum number of concurrent agents allowed.
        """
        self._agents: Dict[str, BaseAgent] = {}
        self._tool_executor = tool_executor
        self._max_agents = max_agents
        self._bus = get_message_bus()

    def spawn(
        self,
        role: str | AgentRole,
        task: Optional[str] = None,
        model: Optional[str] = None,
        name: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> BaseAgent:
        """Spawn a new agent for the given role.

        Args:
            role: Agent role (string or AgentRole enum).
            task: Optional initial task (agent won't auto-execute; call think() yourself).
            model: Override the agent's preferred model.
            name: Custom name for the agent.
            tools: List of tool definitions available to the agent.
            context: Additional context dict for the agent.

        Returns:
            The newly created agent instance.

        Raises:
            ValueError: If the role is unknown or max agents exceeded.
        """
        # Normalize role
        if isinstance(role, str):
            try:
                role_enum = AgentRole(role.lower())
            except ValueError:
                raise ValueError(
                    f"Unknown agent role: {role!r}. "
                    f"Available: {[r.value for r in AgentRole]}"
                )
        else:
            role_enum = role

        # Check capacity
        active_count = len(self.list_active())
        if active_count >= self._max_agents:
            raise ValueError(
                f"Maximum active agents ({self._max_agents}) reached. "
                f"Retire an agent before spawning a new one."
            )

        # Get agent class for this role
        agent_class = ROLE_TO_CLASS.get(role_enum)
        if agent_class is None:
            raise ValueError(f"No agent class registered for role: {role_enum.value}")

        # Create agent
        agent = agent_class(
            name=name,
            model=model,
            tools=tools,
            context=context,
        )

        # Inject tool executor if available
        if self._tool_executor is not None:
            agent.set_tool_executor(self._tool_executor)

        # Track agent
        self._agents[agent.id] = agent

        logger.info(
            "Spawned agent: %s (role=%s, model=%s, id=%s)",
            agent.name,
            agent.role.value,
            agent.model,
            agent.id,
        )

        return agent

    async def retire(self, agent_id: str) -> bool:
        """Retire an agent by ID.

        Args:
            agent_id: The agent's unique identifier.

        Returns:
            True if the agent was found and retired, False otherwise.
        """
        agent = self._agents.get(agent_id)
        if agent is None:
            logger.warning("Attempted to retire unknown agent: %s", agent_id)
            return False

        await agent.retire()
        del self._agents[agent_id]

        logger.info("Retired and removed agent: %s (%s)", agent.name, agent_id)
        return True

    async def retire_all(self) -> int:
        """Retire all tracked agents.

        Returns:
            Number of agents retired.
        """
        count = 0
        for agent_id in list(self._agents.keys()):
            if await self.retire(agent_id):
                count += 1
        return count

    def get(self, agent_id: str) -> Optional[BaseAgent]:
        """Get an agent instance by ID.

        Args:
            agent_id: The agent's unique identifier.

        Returns:
            The agent instance, or None if not found.
        """
        return self._agents.get(agent_id)

    def get_by_role(self, role: str | AgentRole) -> List[BaseAgent]:
        """Get all agents with a specific role.

        Args:
            role: The role to filter by.

        Returns:
            List of matching agents.
        """
        if isinstance(role, str):
            try:
                role_enum = AgentRole(role.lower())
            except ValueError:
                return []
        else:
            role_enum = role

        return [a for a in self._agents.values() if a.role == role_enum]

    def list_active(self) -> List[AgentState]:
        """List all active (non-retired) agents.

        Returns:
            List of AgentState snapshots for active agents.
        """
        active = [
            agent.get_state()
            for agent in self._agents.values()
            if agent.status != AgentStatus.RETIRED
        ]
        return active

    def list_all(self) -> List[AgentState]:
        """List all tracked agents including retired ones.

        Returns:
            List of AgentState snapshots.
        """
        return [agent.get_state() for agent in self._agents.values()]

    async def chat(
        self,
        message: str,
        session_id: Optional[str] = None,
        model: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        """Direct chat without a playbook.

        Creates a temporary agent for the conversation, processes
        the message through the tool system, and returns the response.

        Args:
            message: The user's message.
            session_id: Optional session identifier for context continuity.
            model: Model to use (defaults to heavy model).
            tools: Available tools for the chat agent.

        Returns:
            The agent's response text.
        """
        # Look for existing chat agent for this session
        chat_agent: Optional[BaseAgent] = None

        if session_id:
            for agent in self._agents.values():
                if (
                    agent.role == AgentRole.ORCHESTRATOR
                    and agent.context.get("session_id") == session_id
                    and agent.status != AgentStatus.RETIRED
                ):
                    chat_agent = agent
                    break

        # Create a new chat agent if needed
        if chat_agent is None:
            chat_agent = self.spawn(
                role=AgentRole.ORCHESTRATOR,
                model=model or settings.default_heavy_model,
                name=f"chat-{session_id[:8]}" if session_id else "chat-direct",
                tools=tools,
                context={
                    "session_id": session_id or "ephemeral",
                    "mode": "direct_chat",
                },
            )

        # Execute the think loop
        response = await chat_agent.think(message)

        return response

    async def cleanup_stale(self, max_idle_seconds: int = 600) -> int:
        """Retire agents that have been idle too long.

        Args:
            max_idle_seconds: Maximum idle time before retirement.

        Returns:
            Number of agents retired.
        """
        now = time.time()
        stale_ids = [
            agent_id
            for agent_id, agent in self._agents.items()
            if (now - agent.last_active) > max_idle_seconds
            and agent.status not in (AgentStatus.THINKING, AgentStatus.ACTING)
        ]

        count = 0
        for agent_id in stale_ids:
            if await self.retire(agent_id):
                count += 1

        if count > 0:
            logger.info("Cleaned up %d stale agents", count)

        return count

    @property
    def active_count(self) -> int:
        """Number of currently active agents."""
        return len([
            a for a in self._agents.values()
            if a.status != AgentStatus.RETIRED
        ])

    @property
    def capacity_remaining(self) -> int:
        """Number of additional agents that can be spawned."""
        return max(0, self._max_agents - self.active_count)

    def set_tool_executor(
        self,
        executor: Callable[..., Coroutine[Any, Any, str]],
    ) -> None:
        """Update the tool executor for all current and future agents.

        Args:
            executor: Async callable(name, arguments) -> str.
        """
        self._tool_executor = executor
        # Update existing agents
        for agent in self._agents.values():
            agent.set_tool_executor(executor)


# Global singleton factory
_factory: Optional[AgentFactory] = None


def get_agent_factory() -> AgentFactory:
    """Get or create the global agent factory singleton."""
    global _factory
    if _factory is None:
        _factory = AgentFactory()
    return _factory


def reset_agent_factory() -> None:
    """Reset the global factory (useful for testing)."""
    global _factory
    _factory = None
