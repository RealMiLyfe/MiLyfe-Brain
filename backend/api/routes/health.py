"""Health check endpoint."""

import httpx
from fastapi import APIRouter

from config import settings

router = APIRouter()


@router.get("/health")
async def health_check():
    """System health check — checks all dependencies."""
    status = {"status": "healthy", "services": {}}

    # Check Ollama
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(f"{settings.ollama_base_url}/api/tags")
            status["services"]["ollama"] = "connected" if resp.status_code == 200 else "error"
    except Exception:
        status["services"]["ollama"] = "disconnected"

    # Check ChromaDB
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(f"{settings.chroma_url}/api/v1/heartbeat")
            status["services"]["chromadb"] = "connected" if resp.status_code == 200 else "error"
    except Exception:
        status["services"]["chromadb"] = "disconnected"

    # Check Redis
    try:
        import redis.asyncio as aioredis
        r = aioredis.from_url(settings.redis_url, decode_responses=True)
        await r.ping()
        status["services"]["redis"] = "connected"
        await r.aclose()
    except Exception:
        status["services"]["redis"] = "disconnected"

    # Overall status
    if all(v == "connected" for v in status["services"].values()):
        status["status"] = "healthy"
    elif any(v == "connected" for v in status["services"].values()):
        status["status"] = "degraded"
    else:
        status["status"] = "unhealthy"

    return status
