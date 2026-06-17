"""
MiLyfe Brain - Queue Route

Playbook execution queue status.
"""
from __future__ import annotations

import logging
from typing import Any, Dict

from fastapi import APIRouter
from sqlalchemy import func, select

from memory.database import PlaybookRow, async_session_factory
from models.schemas import PlaybookStatus

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/status")
async def queue_status() -> Dict[str, Any]:
    """Get current queue status with counts of running, waiting, and completed."""
    counts = {
        "running": 0,
        "queued": 0,
        "completed": 0,
        "failed": 0,
        "total": 0,
    }

    if async_session_factory is None:
        return counts

    async with async_session_factory() as session:
        result = await session.execute(
            select(PlaybookRow.status, func.count(PlaybookRow.id))
            .group_by(PlaybookRow.status)
        )
        status_counts = {row[0]: row[1] for row in result.all()}

    counts["running"] = status_counts.get(PlaybookStatus.RUNNING.value, 0)
    counts["queued"] = status_counts.get(PlaybookStatus.QUEUED.value, 0)
    counts["completed"] = status_counts.get(PlaybookStatus.COMPLETED.value, 0)
    counts["failed"] = status_counts.get(PlaybookStatus.FAILED.value, 0)
    counts["total"] = sum(status_counts.values())

    # Include queue manager status
    try:
        from services.queue_manager import queue_manager

        qm_status = queue_manager.get_status()
        counts["queue_manager_running"] = qm_status["running"]
        counts["current_playbook_id"] = qm_status.get("current_playbook_id")
        counts["processed_count"] = qm_status.get("processed_count", 0)
    except Exception:
        pass

    return counts
