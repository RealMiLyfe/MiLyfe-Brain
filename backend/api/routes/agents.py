"""
MiLyfe Brain - Agents Route

Agent management: list roles, view active agents, spawn and retire.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from models.schemas import AgentRole, AgentState

logger = logging.getLogger(__name__)

router = APIRouter()


# In-memory active agents registry
_active_agents: Dict[str, AgentState] = {}


ROLE_DESCRIPTIONS: Dict[str, Dict[str, str]] = {
    AgentRole.ORCHESTRATOR.value: {
        "name": "Conductor",
        "description": "Coordinates tasks, decomposes goals, delegates to specialists.",
    },
    AgentRole.RESEARCHER.value: {
        "name": "Explorer",
        "description": "Web search, documentation lookup, information gathering.",
    },
    AgentRole.CODER.value: {
        "name": "Builder",
        "description": "Writes production-quality code following best practices.",
    },
    AgentRole.EXECUTOR.value: {
        "name": "Runner",
        "description": "Executes shell commands, file operations, and deployments.",
    },
    AgentRole.REVIEWER.value: {
        "name": "Judge",
        "description": "Code review, quality assessment, and testing validation.",
    },
    AgentRole.PLANNER.value: {
        "name": "Strategist",
        "description": "Architecture planning, project roadmaps, and technical strategy.",
    },
    AgentRole.WRITER.value: {
        "name": "Scribe",
        "description": "Documentation, technical writing, and report generation.",
    },
    AgentRole.BROWSER.value: {
        "name": "Navigator",
        "description": "Browser automation, web scraping, and page interaction.",
    },
    AgentRole.GUI.value: {
        "name": "Pilot",
        "description": "GUI automation, desktop interaction, and visual tasks.",
    },
}


class SpawnRequest(BaseModel):
    """Request to spawn a new agent."""
    role: AgentRole
    task: str = Field(..., description="Task to assign to the agent")
    model_override: Optional[str] = Field(default=None, description="Override default model")


@router.get("/roles")
async def list_roles() -> List[Dict[str, str]]:
    """List all 9 agent roles with their descriptions."""
    roles = []
    for role_value, info in ROLE_DESCRIPTIONS.items():
        roles.append({
            "role": role_value,
            "name": info["name"],
            "description": info["description"],
        })
    return roles


@router.get("/active", response_model=List[AgentState])
async def list_active_agents() -> List[AgentState]:
    """List all currently active agents."""
    return list(_active_agents.values())


@router.post("/spawn", response_model=AgentState)
async def spawn_agent(body: SpawnRequest) -> AgentState:
    """Spawn a new agent with a specific role and task."""
    from config import settings
    from datetime import datetime

    if len(_active_agents) >= settings.max_agents:
        raise HTTPException(
            status_code=429,
            detail=f"Maximum agent limit reached ({settings.max_agents})",
        )

    agent_id = str(uuid4())
    agent = AgentState(
        id=agent_id,
        role=body.role,
        status="running",
        current_task=body.task,
        model=body.model_override or settings.default_light_model,
        started_at=datetime.utcnow(),
    )

    _active_agents[agent_id] = agent
    logger.info("Spawned agent %s (role=%s)", agent_id, body.role.value)

    return agent


@router.delete("/{agent_id}")
async def retire_agent(agent_id: str) -> Dict[str, str]:
    """Retire (stop) an active agent."""
    if agent_id not in _active_agents:
        raise HTTPException(status_code=404, detail="Agent not found")

    del _active_agents[agent_id]
    logger.info("Retired agent %s", agent_id)
    return {"status": "retired", "agent_id": agent_id}
