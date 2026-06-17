"""
MiLyfe Brain - Daily Digest Service

Generates a daily summary of system activity: playbooks executed,
tokens consumed, actions performed, and notable events.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


async def generate_daily_digest() -> Dict[str, Any]:
    """
    Generate a digest of yesterday's activity.

    Queries the database for:
      - Playbooks started/completed/failed
      - Total tokens consumed
      - Actions performed
      - Notable events (errors, high-risk actions)

    Returns:
        Dict with structured digest data.
    """
    now = datetime.utcnow()
    yesterday_start = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday_end = yesterday_start + timedelta(days=1)

    digest: Dict[str, Any] = {
        "date": yesterday_start.strftime("%Y-%m-%d"),
        "generated_at": now.isoformat(),
        "playbooks": {
            "total": 0,
            "completed": 0,
            "failed": 0,
            "titles": [],
        },
        "tokens": {
            "total": 0,
            "by_model": {},
        },
        "actions": {
            "total": 0,
            "by_type": {},
        },
        "notable_events": [],
    }

    try:
        from sqlalchemy import func, select

        from memory.database import (
            ActionLogRow,
            PlaybookRow,
            TokenUsageRow,
            async_session_factory,
        )

        if async_session_factory is None:
            logger.warning("Database not available for daily digest")
            return digest

        async with async_session_factory() as session:
            # --- Playbook stats ---
            pb_result = await session.execute(
                select(PlaybookRow)
                .where(PlaybookRow.created_at >= yesterday_start)
                .where(PlaybookRow.created_at < yesterday_end)
            )
            playbooks = pb_result.scalars().all()

            digest["playbooks"]["total"] = len(playbooks)
            digest["playbooks"]["completed"] = sum(
                1 for p in playbooks if p.status == "completed"
            )
            digest["playbooks"]["failed"] = sum(
                1 for p in playbooks if p.status == "failed"
            )
            digest["playbooks"]["titles"] = [p.title for p in playbooks[:10]]

            # --- Token usage ---
            token_result = await session.execute(
                select(
                    TokenUsageRow.model,
                    func.sum(TokenUsageRow.total_tokens),
                )
                .where(TokenUsageRow.timestamp >= yesterday_start)
                .where(TokenUsageRow.timestamp < yesterday_end)
                .group_by(TokenUsageRow.model)
            )
            token_rows = token_result.all()

            total_tokens = 0
            by_model: Dict[str, int] = {}
            for model_name, tokens in token_rows:
                amount = tokens or 0
                by_model[model_name] = amount
                total_tokens += amount

            digest["tokens"]["total"] = total_tokens
            digest["tokens"]["by_model"] = by_model

            # --- Action stats ---
            action_result = await session.execute(
                select(
                    ActionLogRow.action_type,
                    func.count(ActionLogRow.id),
                )
                .where(ActionLogRow.timestamp >= yesterday_start)
                .where(ActionLogRow.timestamp < yesterday_end)
                .group_by(ActionLogRow.action_type)
            )
            action_rows = action_result.all()

            total_actions = 0
            by_type: Dict[str, int] = {}
            for action_type, count in action_rows:
                by_type[action_type] = count or 0
                total_actions += count or 0

            digest["actions"]["total"] = total_actions
            digest["actions"]["by_type"] = by_type

            # --- Notable events (errors, high-risk) ---
            notable_result = await session.execute(
                select(ActionLogRow)
                .where(ActionLogRow.timestamp >= yesterday_start)
                .where(ActionLogRow.timestamp < yesterday_end)
                .where(
                    (ActionLogRow.success == False) |  # noqa: E712
                    (ActionLogRow.risk_level.in_(["high", "critical"]))
                )
                .order_by(ActionLogRow.timestamp.desc())
                .limit(10)
            )
            notable_rows = notable_result.scalars().all()

            digest["notable_events"] = [
                {
                    "action_type": row.action_type,
                    "description": row.description[:200],
                    "risk_level": row.risk_level,
                    "success": row.success,
                    "timestamp": row.timestamp.isoformat() if row.timestamp else None,
                }
                for row in notable_rows
            ]

    except Exception as e:
        logger.error("Failed to generate daily digest: %s", e)
        digest["error"] = str(e)

    logger.info(
        "Daily digest generated: %d playbooks, %d tokens, %d actions",
        digest["playbooks"]["total"],
        digest["tokens"]["total"],
        digest["actions"]["total"],
    )
    return digest
