"""
MiLyfe Brain - Agent Factory

Singleton factory for spawning, managing, and retiring agents.
Provides high-level execute_task and chat interfaces.
"""
from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from config import settings
from models.schemas import AgentRole, AgentState, OutputStyle

from agents.base import BaseAgent
from agents.roles import AGENT_CLASSES

logger = logging.getLogger(__name__)


class AgentFactory:
    """
    Singleton factory that manages agent lifecycle.

    Responsibilities:
    - Spawn agents by role with proper configuration
    - Track active agents and enforce max concurrency
    - Provide execute_task (spawn → think → retire) workflow
    - Provide chat interface for conversational interactions
    """

    _instance: Optional[AgentFactory] = None

    def __new__(cls) -> AgentFactory:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._agents = {}
            cls._instance._chat_agent = None
        return cls._instance

    def __init__(self) -> None:
        # Avoid re-initializing on subsequent calls
        if not hasattr(self, "_initialized"):
            self._agents: Dict[str, BaseAgent] = {}
            self._chat_agent: Optional[BaseAgent] = None
            self._initialized = True

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def active_count(self) -> int:
        """Number of currently active agents."""
        return len(self._agents)

    # ------------------------------------------------------------------
    # Public Methods
    # ------------------------------------------------------------------

    def spawn(
        self,
        role: AgentRole,
        task: str,
        model_override: Optional[str] = None,
        agent_id: Optional[str] = None,
    ) -> AgentState:
        """
        Spawn a new agent of the given role.

        Raises ValueError if max agents exceeded or role not found.
        """
        if len(self._agents) >= settings.max_agents:
            raise ValueError(
                f"Maximum agents ({settings.max_agents}) reached. "
                f"Retire an agent before spawning new ones."
            )

        agent_cls = AGENT_CLASSES.get(role)
        if agent_cls is None:
            raise ValueError(f"Unknown agent role: {role}")

        agent = agent_cls(
            task=task,
            model=model_override,
            agent_id=agent_id,
        )

        self._agents[agent.id] = agent
        logger.info(f"Spawned agent {agent.name} ({agent.id}) for task: {task[:80]}")

        return agent.get_state()

    def retire(self, agent_id: str) -> None:
        """Remove an agent from the active pool."""
        agent = self._agents.pop(agent_id, None)
        if agent:
            logger.info(f"Retired agent {agent.name} ({agent_id})")
        else:
            logger.warning(f"Attempted to retire unknown agent: {agent_id}")

    async def execute_task(
        self,
        role: AgentRole,
        task: str,
        context: Optional[Dict[str, Any]] = None,
        model_override: Optional[str] = None,
    ) -> str:
        """
        Full lifecycle: spawn agent → think → retire → return result.

        This is the primary interface for one-shot task execution.
        """
        state = self.spawn(role=role, task=task, model_override=model_override)
        agent = self._agents.get(state.id)

        if agent is None:
            raise RuntimeError("Agent spawn succeeded but agent not found in pool")

        try:
            start = time.perf_counter()
            result = await agent.think(task=task, context=context)
            elapsed = (time.perf_counter() - start) * 1000

            logger.info(
                f"Agent {agent.name} completed task in {elapsed:.0f}ms "
                f"({agent._total_tokens_used} tokens)"
            )
            return result
        except Exception as e:
            logger.error(f"Agent {agent.name} failed: {e}")
            raise
        finally:
            self.retire(state.id)

    async def send_message(
        self,
        agent_id: str,
        content: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Send a message to an existing agent and get a response."""
        agent = self._agents.get(agent_id)
        if agent is None:
            raise ValueError(f"Agent not found: {agent_id}")

        return await agent.think(task=content, context=context)

    async def chat(
        self,
        message: str,
        session_id: Optional[str] = None,
        model_override: Optional[str] = None,
        output_style: Optional[OutputStyle] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Conversational chat interface. Maintains a persistent chat agent.

        Returns a dict with: response, session_id, tokens_used, model.
        """
        # Ensure a chat agent exists
        if self._chat_agent is None:
            from agents.roles import OrchestratorAgent

            self._chat_agent = OrchestratorAgent(
                task="conversational_assistant",
                model=model_override,
            )
            self._agents[self._chat_agent.id] = self._chat_agent

        agent = self._chat_agent

        # Override model if requested
        if model_override and model_override != agent.model:
            agent.model = model_override

        # Build context with output style and attachments
        context: Dict[str, Any] = {}
        if output_style:
            context["output_style"] = output_style.value
        if attachments:
            attachment_text = "\n".join(
                f"[Attachment: {a.get('filename', 'file')}]\n{a.get('content', '')}"
                for a in attachments
            )
            context["extra"] = attachment_text

        start = time.perf_counter()
        response = await agent.think(task=message, context=context)
        elapsed = (time.perf_counter() - start) * 1000

        return {
            "response": response,
            "session_id": session_id or agent.id,
            "tokens_used": agent._total_tokens_used,
            "model": agent.model,
            "duration_ms": elapsed,
        }

    def get_agent(self, agent_id: str) -> Optional[BaseAgent]:
        """Get an agent by ID, or None if not found."""
        return self._agents.get(agent_id)

    def list_agents(self) -> List[AgentState]:
        """List all active agents with their current state."""
        return [agent.get_state() for agent in self._agents.values()]
