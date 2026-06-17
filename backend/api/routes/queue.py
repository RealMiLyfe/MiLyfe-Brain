"""Queue API — Playbook execution queue status."""

from fastapi import APIRouter

from services.queue_manager import queue_manager

router = APIRouter()


@router.get("/status")
async def get_queue_status() -> dict:
    """Get the current playbook execution queue status."""
    return queue_manager.status()
