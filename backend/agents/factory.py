"""MiLyfe Brain — Agent Factory (spawn, track, retire, chat)."""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

import structlog

from agents.base import BaseAgent
from agents.roles import AGENT_CLASSES
from config import settings
from models.schemas import AgentRole, AgentState, OutputStyle

logger = structlog.get_logger()


class AgentFactory:
    """Creates, manages, and retires agents."""

    def __init__(self):
        self._agents: Dict[str, BaseAgent] = {}
        self._chat_agent: Optional[BaseAgent] = None

    @property
    def active_count(self) -> int:
        return len(self._agents)

    async def spawn(
        self,
        role: AgentRole,
        task: str = "",
        model_override: Optional[str] = None,
        agent_id: Optional[str] = None,
    ) -> AgentState:
        """Spawn a new agent instance."""
        if self.active_count >= settings.max_agents:
            raise RuntimeError(f"Max agents reached ({settings.max_agents})")

        agent_cls = AGENT_CLASSES.get(role)
        if not agent_cls:
            raise ValueError(f"Unknown role: {role}")

        aid = agent_id or str(uuid.uuid4())
        agent = agent_cls(
            role=role,
            agent_id=aid,
            model=model_override,
            task=task,
        )

        self._agents[aid] = agent
        logger.info("agent_spawned", agent_id=aid, role=role.value, model=agent.model)

        # Register in API routes
        try:
            from api.routes.agents import register_agent
            register_agent(agent.get_state())
        except Exception:
            pass

        return agent.get_state()

    async def retire(self, agent_id: str):
        """Retire an agent."""
        agent = self._agents.pop(agent_id, None)
        if agent:
            logger.info("agent_retired", agent_id=agent_id, role=agent.role.value)
            try:
                from api.routes.agents import unregister_agent
                unregister_agent(agent_id)
            except Exception:
                pass

    async def execute_task(
        self,
        role: AgentRole,
        task: str,
        context: Optional[Dict[str, Any]] = None,
        model_override: Optional[str] = None,
    ) -> str:
        """Spawn an agent, execute a task, and retire it."""
        state = await self.spawn(role=role, task=task, model_override=model_override)
        agent = self._agents.get(state.id)
        if not agent:
            raise RuntimeError("Failed to spawn agent")

        try:
            result = await agent.think(task=task, context=context)
            return result
        finally:
            await self.retire(state.id)

    async def send_message(self, agent_id: str, content: str, context: dict = {}) -> str:
        """Send a message to an active agent."""
        agent = self._agents.get(agent_id)
        if not agent:
            raise ValueError(f"Agent {agent_id} not found")
        return await agent.think(task=content, context=context)

    async def chat(
        self,
        message: str,
        session_id: str,
        model_override: Optional[str] = None,
        output_style: OutputStyle = OutputStyle.DEFAULT,
        attachments: List[str] = [],
    ) -> Dict[str, Any]:
        """Handle a chat message using a persistent coder agent."""
        # Use or create a persistent chat agent
        if not self._chat_agent or self._chat_agent.id not in self._agents:
            state = await self.spawn(
                role=AgentRole.CODER,
                task="Interactive chat assistant",
                model_override=model_override or settings.default_heavy_model,
            )
            self._chat_agent = self._agents.get(state.id)

        if not self._chat_agent:
            raise RuntimeError("Failed to create chat agent")

        # Build context with attachments and style
        context = {
            "session_id": session_id,
            "output_style": output_style.value,
        }
        if attachments:
            context["attachments"] = ", ".join(attachments)

        # Apply style prefix
        styled_message = self._apply_style(message, output_style)

        result = await self._chat_agent.think(task=styled_message, context=context)

        return {
            "content": result,
            "model": self._chat_agent.model,
            "tokens_used": 0,  # Tracked separately by token_tracker
            "tool_calls": [],
        }

    def get_agent(self, agent_id: str) -> Optional[BaseAgent]:
        """Get an agent by ID."""
        return self._agents.get(agent_id)

    def list_agents(self) -> List[AgentState]:
        """List all active agents."""
        return [a.get_state() for a in self._agents.values()]

    def _apply_style(self, message: str, style: OutputStyle) -> str:
        """Apply output style instructions to message."""
        style_instructions = {
            OutputStyle.CONCISE: "\n[Style: Be concise. Short answers, minimal explanation.]",
            OutputStyle.VERBOSE: "\n[Style: Be thorough. Explain in detail with examples.]",
            OutputStyle.ARCHITECT: "\n[Style: Think like a senior architect. Focus on design decisions.]",
            OutputStyle.PAIR_PROGRAMMER: "\n[Style: Act as a pair programmer. Think out loud, suggest alternatives.]",
            OutputStyle.DIFF_ONLY: "\n[Style: Only show code diffs. No explanation unless asked.]",
            OutputStyle.JUNIOR_FRIENDLY: "\n[Style: Explain for a junior developer. Be patient and thorough.]",
            OutputStyle.TUTORIAL: "\n[Style: Write as a tutorial. Step by step with explanations.]",
        }
        suffix = style_instructions.get(style, "")
        return message + suffix


# Singleton
agent_factory = AgentFactory()
