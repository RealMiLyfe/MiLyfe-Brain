"""Tokens API — LLM token usage statistics."""

from fastapi import APIRouter, Query

from services.token_tracker import token_tracker

router = APIRouter()


@router.get("/stats")
async def get_token_stats(days: int = Query(7, ge=1, le=90)) -> dict:
    """Get token usage statistics for the specified period."""
    stats = await token_tracker.get_stats(days=days)
    return stats
