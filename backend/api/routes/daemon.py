"""Daemon/Brain API — Daemon status, skills, memory, and digest."""

from fastapi import APIRouter

from services.daemon import daemon_service
from services.skill_library import skill_library

router = APIRouter()


@router.get("/daemon/status")
async def get_daemon_status() -> dict:
    """Get the file watcher daemon status."""
    return daemon_service.status()


@router.get("/skills")
async def list_skills() -> dict:
    """List all learned skills."""
    skills = await skill_library.list_skills()
    return {"skills": skills, "count": len(skills)}


@router.get("/memory")
async def get_memory_stats() -> dict:
    """Get agent memory statistics."""
    from memory.database import async_session_factory, AgentMemoryModel
    from sqlalchemy import func, select

    async with async_session_factory() as db:
        result = await db.execute(
            select(func.count(AgentMemoryModel.id))
        )
        count = result.scalar() or 0

        role_result = await db.execute(
            select(
                AgentMemoryModel.role,
                func.count(AgentMemoryModel.id),
            ).group_by(AgentMemoryModel.role)
        )
        by_role = {row[0]: row[1] for row in role_result.all()}

    return {
        "total_memories": count,
        "by_role": by_role,
    }


@router.get("/digest")
async def get_brain_digest() -> dict:
    """Get a high-level brain activity digest."""
    from memory.database import async_session_factory, PlaybookModel, ActionLogModel
    from sqlalchemy import func, select
    from datetime import datetime, timedelta

    since = datetime.utcnow() - timedelta(hours=24)

    async with async_session_factory() as db:
        # Playbooks in last 24h
        pb_result = await db.execute(
            select(func.count(PlaybookModel.id)).where(
                PlaybookModel.created_at >= since
            )
        )
        playbooks_24h = pb_result.scalar() or 0

        # Actions in last 24h
        action_result = await db.execute(
            select(func.count(ActionLogModel.id)).where(
                ActionLogModel.timestamp >= since
            )
        )
        actions_24h = action_result.scalar() or 0

    from agents.factory import get_agent_factory
    factory = get_agent_factory()

    return {
        "period": "24h",
        "playbooks_created": playbooks_24h,
        "actions_performed": actions_24h,
        "active_agents": factory.active_count,
        "daemon": daemon_service.status(),
    }
