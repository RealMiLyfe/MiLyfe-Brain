"""MiLyfe Brain — Playbook Execution Queue Routes."""

from __future__ import annotations

from fastapi import APIRouter

from models.schemas import QueueStatus

router = APIRouter()


@router.get("/status", response_model=QueueStatus)
async def get_queue_status():
    """Get current queue state."""
    try:
        from services.queue_manager import queue_manager
        return await queue_manager.get_status()
    except Exception:
        return QueueStatus()
