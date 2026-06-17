"""MiLyfe Brain — Token Usage Statistics Routes."""

from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import select, func

from memory.database import TokenUsageRow, async_session_factory
from models.schemas import TokenStats

router = APIRouter()

# Approximate cost per 1K tokens for comparison
_COST_MAP = {
    "gpt-4": 0.03,
    "gpt-3.5-turbo": 0.002,
    "claude-3-opus": 0.015,
}


@router.get("/stats", response_model=TokenStats)
async def get_token_stats():
    """Get token usage statistics."""
    async with async_session_factory() as session:
        # Total tokens
        result = await session.execute(
            select(
                func.sum(TokenUsageRow.prompt_tokens),
                func.sum(TokenUsageRow.completion_tokens),
                func.sum(TokenUsageRow.total_tokens),
            )
        )
        row = result.one()
        total_prompt = row[0] or 0
        total_completion = row[1] or 0
        total = row[2] or 0

        # By model
        result2 = await session.execute(
            select(TokenUsageRow.model, func.sum(TokenUsageRow.total_tokens))
            .group_by(TokenUsageRow.model)
        )
        by_model = {r[0]: r[1] for r in result2.all()}

        # By role
        result3 = await session.execute(
            select(TokenUsageRow.agent_role, func.sum(TokenUsageRow.total_tokens))
            .group_by(TokenUsageRow.agent_role)
        )
        by_role = {r[0]: r[1] for r in result3.all() if r[0]}

    # Calculate equivalent cost (what this would cost on GPT-4)
    cost_equiv = (total / 1000) * _COST_MAP.get("gpt-4", 0.03)

    return TokenStats(
        total_prompt_tokens=total_prompt,
        total_completion_tokens=total_completion,
        total_tokens=total,
        by_model=by_model,
        by_role=by_role,
        cost_equivalent_usd=round(cost_equiv, 4),
    )


@router.get("/history")
async def get_token_history(limit: int = 100):
    """Get recent token usage entries."""
    async with async_session_factory() as session:
        result = await session.execute(
            select(TokenUsageRow).order_by(TokenUsageRow.timestamp.desc()).limit(limit)
        )
        rows = result.scalars().all()
        return [
            {
                "id": r.id,
                "model": r.model,
                "agent_role": r.agent_role,
                "prompt_tokens": r.prompt_tokens,
                "completion_tokens": r.completion_tokens,
                "total_tokens": r.total_tokens,
                "timestamp": r.timestamp.isoformat() if r.timestamp else None,
            }
            for r in rows
        ]
