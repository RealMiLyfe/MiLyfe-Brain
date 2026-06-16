"""Agent management routes — spawn, list, retire, message."""

from fastapi import APIRouter, HTTPException

from agents.factory import agent_factory
from agents.roles import AGENT_ROLES
from models.schemas import AgentMessageRequest, AgentSpawnRequest, AgentState

router = APIRouter()


@router.get("/roles")
async def list_roles():
    """List available agent roles."""
    return [
        {
            "role": role,
            "name": info["name"],
            "description": info["description"],
            "preferred_model": info["preferred_model"],
        }
        for role, info in AGENT_ROLES.items()
    ]


@router.get("/active", response_model=list[AgentState])
async def list_active_agents():
    """List currently active agents."""
    return agent_factory.list_active()


@router.post("/spawn", response_model=AgentState)
async def spawn_agent(request: AgentSpawnRequest):
    """Spawn a new agent."""
    try:
        agent = agent_factory.spawn(request.role.value, model=request.model)
        return agent.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{agent_id}/message")
async def send_message_to_agent(agent_id: str, request: AgentMessageRequest):
    """Send a message/task to a specific agent."""
    agent = agent_factory.get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    result = await agent.think(request.message, context=request.context)
    return {
        "agent_id": agent_id,
        "response": result.get("response", ""),
        "tool_calls": result.get("tool_calls", []),
        "error": result.get("error"),
    }


@router.delete("/{agent_id}")
async def retire_agent(agent_id: str):
    """Retire an agent."""
    success = agent_factory.retire(agent_id)
    if not success:
        raise HTTPException(status_code=404, detail="Agent not found")
    return {"message": "Agent retired", "agent_id": agent_id}
