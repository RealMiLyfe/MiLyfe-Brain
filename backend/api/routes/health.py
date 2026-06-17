"""
MiLyfe Brain - Health Check Route

GET /health → system health status with connectivity checks.
"""
from __future__ import annotations

import logging
import time
from typing import Any, Dict

import httpx
from fastapi import APIRouter

from config import settings
from models.schemas import HealthStatus

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health", response_model=HealthStatus)
async def health_check() -> HealthStatus:
    """Check system health including connectivity to Ollama, ChromaDB, Redis, and Database."""
    from main import get_uptime

    status = HealthStatus(
        status="healthy",
        version="0.1.0",
        uptime_seconds=get_uptime(),
    )

    # Check Ollama connectivity
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(f"{settings.ollama_base_url}/api/tags")
            status.ollama_connected = resp.status_code == 200
    except Exception:
        status.ollama_connected = False

    # Check ChromaDB connectivity
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(f"{settings.chroma_url}/api/v1/heartbeat")
            status.chroma_connected = resp.status_code == 200
    except Exception:
        status.chroma_connected = False

    # Check Redis connectivity
    try:
        import redis.asyncio as aioredis

        r = aioredis.from_url(settings.redis_url, socket_timeout=2.0)
        await r.ping()
        status.redis_connected = True
        await r.aclose()
    except Exception:
        status.redis_connected = False

    # Check Database connectivity
    try:
        from memory.database import async_session_factory

        if async_session_factory is not None:
            async with async_session_factory() as session:
                await session.execute("SELECT 1")  # type: ignore[arg-type]
            status.database_connected = True
        else:
            status.database_connected = False
    except Exception:
        status.database_connected = False

    # Determine overall status
    if not status.ollama_connected and not status.database_connected:
        status.status = "unhealthy"
    elif not status.ollama_connected or not status.chroma_connected:
        status.status = "degraded"

    # Active agents count
    try:
        from agents.factory import agent_factory

        status.active_agents = len(agent_factory.get_active_agents())
    except Exception:
        status.active_agents = 0

    return status
