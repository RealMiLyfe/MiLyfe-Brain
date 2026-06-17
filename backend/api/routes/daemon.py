"""
MiLyfe Brain - Daemon Route

Background daemon status and control.
"""
from __future__ import annotations

import logging
from typing import Dict

from fastapi import APIRouter, HTTPException

from models.schemas import DaemonStatus

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/status", response_model=DaemonStatus)
async def get_daemon_status() -> DaemonStatus:
    """Get daemon status."""
    try:
        from services.daemon import daemon

        status = daemon.get_status()
        return DaemonStatus(
            running=status["running"],
            uptime_seconds=status["uptime_seconds"],
            last_heartbeat=None,
        )
    except Exception as e:
        logger.error("Failed to get daemon status: %s", e)
        return DaemonStatus(running=False)


@router.post("/start")
async def start_daemon() -> Dict[str, str]:
    """Start the background daemon."""
    try:
        from services.daemon import daemon

        if daemon._running:
            return {"status": "already_running"}

        await daemon.start()
        return {"status": "started"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start daemon: {str(e)}")


@router.post("/stop")
async def stop_daemon() -> Dict[str, str]:
    """Stop the background daemon."""
    try:
        from services.daemon import daemon

        if not daemon._running:
            return {"status": "already_stopped"}

        await daemon.stop()
        return {"status": "stopped"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to stop daemon: {str(e)}")
