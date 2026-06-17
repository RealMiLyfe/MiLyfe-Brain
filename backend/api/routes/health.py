"""MiLyfe Brain — Health Check Endpoint."""

from fastapi import APIRouter

from config import settings
from models.schemas import HealthStatus

router = APIRouter()


@router.get("/health", response_model=HealthStatus, tags=["health"])
async def health_check():
    """Health check endpoint."""
    import httpx
    from main import get_uptime

    services = {}

    # Check Ollama
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(f"{settings.ollama_base_url}/api/tags")
            services["ollama"] = "healthy" if resp.status_code == 200 else "unhealthy"
    except Exception:
        services["ollama"] = "unavailable"

    # Check ChromaDB
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(f"{settings.chroma_url}/api/v1/heartbeat")
            services["chromadb"] = "healthy" if resp.status_code == 200 else "unhealthy"
    except Exception:
        services["chromadb"] = "unavailable"

    # Check Redis
    try:
        import redis.asyncio as aioredis
        r = aioredis.from_url(settings.redis_url, decode_responses=True)
        await r.ping()
        services["redis"] = "healthy"
        await r.close()
    except Exception:
        services["redis"] = "unavailable"

    # Check SQLite
    try:
        from memory.database import async_session_factory
        from sqlalchemy import text
        async with async_session_factory() as session:
            await session.execute(text("SELECT 1"))
        services["database"] = "healthy"
    except Exception:
        services["database"] = "unhealthy"

    overall = "healthy" if all(v == "healthy" for v in services.values() if v != "unavailable") else "degraded"

    return HealthStatus(
        status=overall,
        version="1.0.0",
        services=services,
        uptime_seconds=get_uptime(),
    )
