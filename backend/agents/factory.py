"""AgentFactory — Spawn, track, and retire agents."""

import structlog
from typing import Optional

from agents.base import BaseAgent
from agents.roles import AGENT_ROLES
from config import settings

logger = structlog.get_logger()


class AgentFactory:
    """Central factory for creating and managing agent instances."""

    def __init__(self):
        self._agents: dict[str, BaseAgent] = {}

    @property
    def active_agents(self) -> dict[str, BaseAgent]:
        """Get all active agents."""
        return {aid: agent for aid, agent in self._agents.items() if agent.status != "retired"}

    def spawn(self, role: str, model: Optional[str] = None) -> BaseAgent:
        """Spawn a new agent of the specified role.

        Args:
            role: One of the 9 agent roles
            model: Override the default model for this agent

        Returns:
            The spawned agent instance

        Raises:
            ValueError: If role is invalid or max agents reached
        """
        if role not in AGENT_ROLES:
            raise ValueError(f"Unknown agent role: {role}. Valid roles: {list(AGENT_ROLES.keys())}")

        if len(self.active_agents) >= settings.max_agents:
            raise ValueError(f"Maximum agents ({settings.max_agents}) reached. Retire an agent first.")

        role_config = AGENT_ROLES[role]
        agent_class = role_config["class"]

        # Use preferred model if none specified
        agent_model = model or role_config.get("preferred_model", settings.default_heavy_model)

        agent = agent_class(model=agent_model)
        self._agents[agent.id] = agent

        logger.info(
            "Agent spawned",
            agent_id=agent.id,
            role=role,
            name=agent.name,
            model=agent_model,
        )

        return agent

    def get(self, agent_id: str) -> Optional[BaseAgent]:
        """Get an agent by ID."""
        return self._agents.get(agent_id)

    def retire(self, agent_id: str) -> bool:
        """Retire an agent (mark as inactive, remove from active pool).

        Returns:
            True if agent was found and retired, False otherwise
        """
        agent = self._agents.get(agent_id)
        if agent:
            agent.status = "retired"
            logger.info("Agent retired", agent_id=agent_id, role=agent.role, name=agent.name)
            return True
        return False

    def retire_all(self) -> int:
        """Retire all active agents. Returns count retired."""
        count = 0
        for agent in list(self._agents.values()):
            if agent.status != "retired":
                agent.status = "retired"
                count += 1
        logger.info("All agents retired", count=count)
        return count

    def list_active(self) -> list[dict]:
        """List all active agents as dictionaries."""
        return [agent.to_dict() for agent in self.active_agents.values()]

    def get_by_role(self, role: str) -> Optional[BaseAgent]:
        """Get first active agent with the specified role."""
        for agent in self.active_agents.values():
            if agent.role == role:
                return agent
        return None

    def spawn_or_get(self, role: str, model: Optional[str] = None) -> BaseAgent:
        """Get an existing agent with the role, or spawn a new one."""
        existing = self.get_by_role(role)
        if existing:
            return existing
        return self.spawn(role, model)


# Global factory instance
agent_factory = AgentFactory()
