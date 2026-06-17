"""MiLyfe Brain — Autonomous Daemon Control Routes."""

from __future__ import annotations

from fastapi import APIRouter

from models.schemas import DaemonStatus

router = APIRouter()


@router.get("/status", response_model=DaemonStatus)
async def get_daemon_status():
    """Get daemon status."""
    try:
        from services.daemon import daemon_service
        return daemon_service.get_status()
    except Exception:
        return DaemonStatus(running=False)


@router.post("/start")
async def start_daemon():
    """Start the autonomous daemon."""
    try:
        from services.daemon import daemon_service
        await daemon_service.start()
        return {"detail": "Daemon started"}
    except Exception as e:
        return {"detail": f"Failed: {e}"}


@router.post("/stop")
async def stop_daemon():
    """Stop the autonomous daemon."""
    try:
        from services.daemon import daemon_service
        await daemon_service.stop()
        return {"detail": "Daemon stopped"}
    except Exception as e:
        return {"detail": f"Failed: {e}"}
