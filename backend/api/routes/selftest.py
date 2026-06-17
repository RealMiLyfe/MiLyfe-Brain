"""Self-test API — Run system diagnostics."""

import httpx
from fastapi import APIRouter

from config import settings

router = APIRouter()


@router.post("/run")
async def run_selftest() -> dict:
    """Run a full system self-test checking all subsystems."""
    results = {}

    # Test database
    try:
        from memory.database import async_session_factory
        async with async_session_factory() as db:
            await db.execute("SELECT 1")  # type: ignore
        results["database"] = {"status": "ok"}
    except Exception as e:
        results["database"] = {"status": "error", "detail": str(e)}

    # Test Ollama
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"{settings.ollama_base_url}/api/tags")
            if resp.status_code == 200:
                models = [m["name"] for m in resp.json().get("models", [])]
                results["ollama"] = {"status": "ok", "models": models[:5]}
            else:
                results["ollama"] = {"status": "error", "code": resp.status_code}
    except Exception as e:
        results["ollama"] = {"status": "unreachable", "detail": str(e)}

    # Test ChromaDB
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"{settings.chromadb_url}/api/v1/heartbeat")
            results["chromadb"] = {
                "status": "ok" if resp.status_code == 200 else "error"
            }
    except Exception as e:
        results["chromadb"] = {"status": "unreachable", "detail": str(e)}

    # Test workspace
    import os
    ws = settings.workspace_dir
    results["workspace"] = {
        "status": "ok" if os.path.exists(ws) else "missing",
        "path": ws,
        "writable": os.access(ws, os.W_OK) if os.path.exists(ws) else False,
    }

    # Overall status
    all_ok = all(r.get("status") == "ok" for r in results.values())

    return {
        "overall": "healthy" if all_ok else "degraded",
        "results": results,
    }
