"""
MiLyfe Brain - Tokens Route

Token usage statistics and history.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List

from fastapi import APIRouter, Query
from sqlalchemy import func, select

from memory.database import TokenUsageRow, async_session_factory
from models.schemas import TokenStats, TokenUsage

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/stats", response_model=TokenStats)
async def get_token_stats(
    days: int = Query(default=30, ge=1, le=365),
) -> TokenStats:
    """Get aggregated token usage statistics."""
    try:
        from services.token_tracker import token_tracker

        stats = await token_tracker.get_usage_stats(days=days)

        return TokenStats(
            total_prompt_tokens=0,
            total_completion_tokens=0,
            total_tokens=stats.get("total_tokens", 0),
            by_model=stats.get("by_model", {}),
            by_role=stats.get("by_role", {}),
            period_start=datetime.utcnow() - timedelta(days=days),
            period_end=datetime.utcnow(),
        )
    except Exception as e:
        logger.error("Failed to get token stats: %s", e)
        return TokenStats()


@router.get("/history", response_model=List[TokenUsage])
async def get_token_history(
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    model: str = Query(default=None),
) -> List[TokenUsage]:
    """Get recent token usage entries."""
    if async_session_factory is None:
        return []

    async with async_session_factory() as session:
        query = select(TokenUsageRow).order_by(TokenUsageRow.timestamp.desc())

        if model:
            query = query.where(TokenUsageRow.model == model)

        query = query.offset(offset).limit(limit)

        result = await session.execute(query)
        rows = result.scalars().all()

    return [
        TokenUsage(
            id=row.id,
            model=row.model,
            prompt_tokens=row.prompt_tokens,
            completion_tokens=row.completion_tokens,
            total_tokens=row.total_tokens,
            playbook_id=row.playbook_id,
            agent_role=row.agent_role,
            timestamp=row.timestamp,
        )
        for row in rows
    ]
