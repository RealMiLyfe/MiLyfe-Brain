"""Autonomous daemon, skills, memory, and digest routes."""

from fastapi import APIRouter

from models.schemas import DaemonStatus, DigestResponse, MemoryResponse, SkillResponse

router = APIRouter()


@router.get("/daemon/status", response_model=DaemonStatus)
async def get_daemon_status():
    """Get autonomous daemon status."""
    from services.daemon import daemon_service

    return daemon_service.get_status()


@router.post("/daemon/start")
async def start_daemon():
    """Start the autonomous daemon."""
    import asyncio
    from services.daemon import daemon_service

    asyncio.create_task(daemon_service.run())
    return {"message": "Daemon started"}


@router.post("/daemon/stop")
async def stop_daemon():
    """Stop the autonomous daemon."""
    from services.daemon import daemon_service

    daemon_service.stop()
    return {"message": "Daemon stopped"}


@router.get("/skills", response_model=list[SkillResponse])
async def list_skills():
    """List learned skills."""
    from memory.database import db

    rows = await db.fetch_all("SELECT * FROM skills ORDER BY success_count DESC")
    return [
        SkillResponse(
            id=row["id"],
            name=row["name"],
            description=row["description"],
            category=row["category"],
            success_count=row["success_count"],
            created_at=row["created_at"],
        )
        for row in rows
    ]


@router.get("/memory", response_model=list[MemoryResponse])
async def get_memories(role: str = None, limit: int = 50):
    """Get agent memories."""
    from memory.database import db

    if role:
        rows = await db.fetch_all(
            "SELECT * FROM agent_memories WHERE role = ? ORDER BY importance DESC LIMIT ?",
            (role, limit),
        )
    else:
        rows = await db.fetch_all(
            "SELECT * FROM agent_memories ORDER BY importance DESC LIMIT ?", (limit,)
        )

    return [
        MemoryResponse(
            id=row["id"],
            role=row["role"],
            memory_type=row["memory_type"],
            content=row["content"],
            importance=row["importance"],
            recall_count=row["recall_count"],
            created_at=row["created_at"],
        )
        for row in rows
    ]


@router.get("/digest", response_model=DigestResponse)
async def get_daily_digest():
    """Get today's daily digest."""
    from services.daily_digest import daily_digest_service

    return await daily_digest_service.generate()
