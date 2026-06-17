"""MiLyfe Brain — Agent Management Routes."""

from __future__ import annotations

from typing import Dict, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from models.schemas import AgentRole, AgentState

router = APIRouter()

# In-memory active agents registry
_active_agents: Dict[str, AgentState] = {}


class SpawnRequest(BaseModel):
    role: AgentRole
    task: str = ""
    model_override: Optional[str] = None


class AgentMessage(BaseModel):
    content: str
    context: dict = {}


@router.get("/roles")
async def list_roles():
    """List available agent roles."""
    role_info = {
        AgentRole.ORCHESTRATOR: {"name": "Conductor", "purpose": "Breaks tasks, assigns work, coordinates"},
        AgentRole.RESEARCHER: {"name": "Explorer", "purpose": "Web search, documentation, context gathering"},
        AgentRole.CODER: {"name": "Builder", "purpose": "Writes production code"},
        AgentRole.EXECUTOR: {"name": "Runner", "purpose": "File ops, shell commands, deployment"},
        AgentRole.CRITIC: {"name": "Judge", "purpose": "Code review, quality checks, testing"},
        AgentRole.DESIGNER: {"name": "Architect", "purpose": "UI/UX design, system architecture"},
        AgentRole.WRITER: {"name": "Scribe", "purpose": "Documentation, READMEs, reports"},
        AgentRole.DEBUGGER: {"name": "Detective", "purpose": "Error diagnosis, fix suggestions"},
        AgentRole.PLANNER: {"name": "Strategist", "purpose": "Architecture, planning, task decomposition"},
    }
    return [
        {"role": role.value, **info}
        for role, info in role_info.items()
    ]


@router.get("/active", response_model=List[AgentState])
async def list_active_agents():
    """List currently active agents."""
    return list(_active_agents.values())


@router.post("/spawn", response_model=AgentState)
async def spawn_agent(req: SpawnRequest):
    """Spawn a new agent."""
    from agents.factory import agent_factory

    try:
        agent_state = await agent_factory.spawn(
            role=req.role,
            task=req.task,
            model_override=req.model_override,
        )
        _active_agents[agent_state.id] = agent_state
        return agent_state
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to spawn agent: {e}")


@router.post("/{agent_id}/message")
async def send_message_to_agent(agent_id: str, msg: AgentMessage):
    """Send a message to a specific agent."""
    if agent_id not in _active_agents:
        raise HTTPException(status_code=404, detail="Agent not found")

    from agents.factory import agent_factory

    try:
        response = await agent_factory.send_message(agent_id, msg.content, msg.context)
        return {"agent_id": agent_id, "response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{agent_id}")
async def retire_agent(agent_id: str):
    """Retire an agent."""
    if agent_id not in _active_agents:
        raise HTTPException(status_code=404, detail="Agent not found")

    from agents.factory import agent_factory
    await agent_factory.retire(agent_id)
    del _active_agents[agent_id]

    return {"detail": "Agent retired", "id": agent_id}


def register_agent(state: AgentState):
    """Register an agent in the active registry (called by factory)."""
    _active_agents[state.id] = state


def unregister_agent(agent_id: str):
    """Remove agent from registry."""
    _active_agents.pop(agent_id, None)


def get_active_agents() -> Dict[str, AgentState]:
    """Get all active agents."""
    return _active_agents
