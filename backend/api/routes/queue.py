"""Playbook execution queue routes."""

from fastapi import APIRouter

from models.schemas import QueueStatus

router = APIRouter()


@router.get("/status", response_model=QueueStatus)
async def get_queue_status():
    """Get current queue state (running/waiting/completed)."""
    from services.queue_manager import queue_manager

    return queue_manager.get_status()


@router.post("/pause")
async def pause_queue():
    """Pause queue processing."""
    from services.queue_manager import queue_manager

    queue_manager.pause()
    return {"message": "Queue paused"}


@router.post("/resume")
async def resume_queue():
    """Resume queue processing."""
    from services.queue_manager import queue_manager

    queue_manager.resume()
    return {"message": "Queue resumed"}


@router.post("/clear")
async def clear_queue():
    """Clear all waiting items from queue."""
    from services.queue_manager import queue_manager

    count = queue_manager.clear_waiting()
    return {"message": f"Cleared {count} items from queue"}
