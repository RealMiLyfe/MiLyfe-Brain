"""Agents API — Agent lifecycle management."""

from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from agents.base import AgentRole
from agents.factory import get_agent_factory

router = APIRouter()


class SpawnRequest(BaseModel):
    """Request body for spawning an agent."""
    role: str
    name: Optional[str] = None
    model: Optional[str] = None
    task: Optional[str] = None


class MessageRequest(BaseModel):
    """Request body for sending a message to an agent."""
    message: str


@router.get("/roles")
async def list_roles() -> dict:
    """List all available agent roles."""
    return {
        "roles": [
            {"value": r.value, "label": r.value.title()}
            for r in AgentRole
        ]
    }


@router.get("/active")
async def list_active_agents() -> dict:
    """List all currently active agents."""
    factory = get_agent_factory()
    agents = factory.list_active()
    return {
        "agents": [
            {
                "id": a.id,
                "role": a.role,
                "name": a.name,
                "status": a.status,
                "model": a.model,
                "actions_taken": a.actions_taken,
                "thoughts_count": a.thoughts_count,
                "created_at": a.created_at,
                "last_active": a.last_active,
            }
            for a in agents
        ],
        "count": len(agents),
        "capacity_remaining": factory.capacity_remaining,
    }


@router.post("/spawn")
async def spawn_agent(body: SpawnRequest) -> dict:
    """Spawn a new agent with the given role."""
    factory = get_agent_factory()

    try:
        agent = factory.spawn(
            role=body.role,
            name=body.name,
            model=body.model,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # If a task is provided, execute it
    result = None
    if body.task:
        result = await agent.think(body.task)

    return {
        "id": agent.id,
        "name": agent.name,
        "role": agent.role.value,
        "status": agent.status.value,
        "model": agent.model,
        "result": result,
    }


@router.post("/{agent_id}/message")
async def send_message_to_agent(agent_id: str, body: MessageRequest) -> dict:
    """Send a message to a specific agent and get a response."""
    factory = get_agent_factory()
    agent = factory.get(agent_id)

    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")

    result = await agent.think(body.message)

    return {
        "agent_id": agent_id,
        "response": result,
        "status": agent.status.value,
        "actions_taken": agent.actions_taken,
    }


@router.delete("/{agent_id}")
async def retire_agent(agent_id: str) -> dict:
    """Retire (destroy) an agent."""
    factory = get_agent_factory()
    success = await factory.retire(agent_id)

    if not success:
        raise HTTPException(status_code=404, detail="Agent not found")

    return {"message": "Agent retired", "agent_id": agent_id}
