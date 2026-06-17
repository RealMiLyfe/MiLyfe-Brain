"""Health check endpoint."""

import time

import httpx
from fastapi import APIRouter, Request

from config import settings
from models.schemas import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check(request: Request) -> HealthResponse:
    """System health check with service connectivity status."""
    start_time = getattr(request.app.state, "start_time", time.time())
    uptime = time.time() - start_time

    ollama_connected = False
    models_available = []

    try:
        async with httpx.AsyncClient(timeout=3) as client:
            resp = await client.get(f"{settings.ollama_base_url}/api/tags")
            if resp.status_code == 200:
                ollama_connected = True
                models_available = [
                    m["name"] for m in resp.json().get("models", [])
                ][:10]
    except Exception:
        pass

    chromadb_connected = False
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            resp = await client.get(f"{settings.chromadb_url}/api/v1/heartbeat")
            chromadb_connected = resp.status_code == 200
    except Exception:
        pass

    return HealthResponse(
        status="healthy",
        version=settings.app_version,
        uptime_seconds=round(uptime, 1),
        ollama_connected=ollama_connected,
        chromadb_connected=chromadb_connected,
        database_connected=True,
        models_available=models_available,
    )
