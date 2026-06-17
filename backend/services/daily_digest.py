"""MiLyfe Brain — Daily Digest (Morning Summary Generation)."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, List

import structlog
from sqlalchemy import select, func

logger = structlog.get_logger()


async def generate_daily_digest() -> Dict:
    """Generate a summary of yesterday's activity."""
    from memory.database import (
        ActionLogRow, PlaybookRow, TokenUsageRow,
        async_session_factory,
    )

    yesterday = datetime.utcnow() - timedelta(days=1)

    async with async_session_factory() as session:
        # Playbooks run
        pb_result = await session.execute(
            select(func.count(PlaybookRow.id))
            .where(PlaybookRow.created_at >= yesterday)
        )
        playbooks_run = pb_result.scalar() or 0

        # Completed
        pb_completed = await session.execute(
            select(func.count(PlaybookRow.id))
            .where(PlaybookRow.status == "completed")
            .where(PlaybookRow.completed_at >= yesterday)
        )
        completed = pb_completed.scalar() or 0

        # Actions performed
        actions_result = await session.execute(
            select(func.count(ActionLogRow.id))
            .where(ActionLogRow.timestamp >= yesterday)
        )
        total_actions = actions_result.scalar() or 0

        # Tokens used
        tokens_result = await session.execute(
            select(func.sum(TokenUsageRow.total_tokens))
            .where(TokenUsageRow.timestamp >= yesterday)
        )
        total_tokens = tokens_result.scalar() or 0

        # Most active agent role
        role_result = await session.execute(
            select(ActionLogRow.agent_role, func.count(ActionLogRow.id))
            .where(ActionLogRow.timestamp >= yesterday)
            .group_by(ActionLogRow.agent_role)
            .order_by(func.count(ActionLogRow.id).desc())
            .limit(1)
        )
        top_role_row = role_result.first()
        top_role = top_role_row[0] if top_role_row else "none"

    digest = {
        "date": yesterday.strftime("%Y-%m-%d"),
        "playbooks_run": playbooks_run,
        "playbooks_completed": completed,
        "success_rate": f"{(completed/playbooks_run*100):.0f}%" if playbooks_run > 0 else "N/A",
        "total_actions": total_actions,
        "total_tokens": total_tokens,
        "cost_equivalent_usd": round(total_tokens / 1000 * 0.03, 4),
        "most_active_role": top_role,
        "generated_at": datetime.utcnow().isoformat(),
    }

    logger.info("daily_digest_generated", **digest)
    return digest
