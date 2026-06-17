"""
MiLyfe Brain - Token Tracker Service

Records token usage per LLM call. Writes to TokenUsageRow in the database.
Provides aggregation queries for analytics.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Dict, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)


class TokenTracker:
    """Tracks and records LLM token usage per agent and model."""

    def __init__(self) -> None:
        self._total_tokens: int = 0
        self._session_usage: Dict[str, int] = {}  # model -> total_tokens

    async def record(
        self,
        agent_id: str,
        agent_role: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        playbook_id: Optional[str] = None,
    ) -> None:
        """
        Record token usage for a single LLM call.

        Args:
            agent_id: ID of the agent that made the call.
            agent_role: Role of the agent (e.g., 'coder', 'planner').
            model: Model name used.
            prompt_tokens: Number of prompt/input tokens.
            completion_tokens: Number of completion/output tokens.
            playbook_id: Optional associated playbook ID.
        """
        total = prompt_tokens + completion_tokens
        self._total_tokens += total
        self._session_usage[model] = self._session_usage.get(model, 0) + total

        try:
            from memory.database import TokenUsageRow, async_session_factory

            if async_session_factory is None:
                logger.debug(
                    "Token usage (in-memory): model=%s prompt=%d completion=%d",
                    model, prompt_tokens, completion_tokens,
                )
                return

            async with async_session_factory() as session:
                row = TokenUsageRow(
                    id=str(uuid4()),
                    model=model,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=total,
                    playbook_id=playbook_id,
                    agent_role=agent_role,
                    timestamp=datetime.utcnow(),
                )
                session.add(row)
                await session.commit()

            logger.debug(
                "Token usage recorded: agent=%s model=%s prompt=%d completion=%d total=%d",
                agent_role, model, prompt_tokens, completion_tokens, total,
            )
        except Exception as e:
            logger.error("Failed to record token usage: %s", e)

    async def get_totals(self) -> Dict[str, int]:
        """Get session-level token totals by model."""
        return {
            "total_tokens": self._total_tokens,
            "by_model": dict(self._session_usage),
        }

    async def get_usage_stats(self, days: int = 30) -> Dict:
        """
        Query aggregated token usage stats from the database.

        Args:
            days: Number of days to look back.

        Returns:
            Dict with total tokens, per-model breakdown, per-role breakdown.
        """
        from datetime import timedelta

        try:
            from sqlalchemy import func, select

            from memory.database import TokenUsageRow, async_session_factory

            if async_session_factory is None:
                return {"total_tokens": self._total_tokens, "by_model": self._session_usage}

            since = datetime.utcnow() - timedelta(days=days)

            async with async_session_factory() as session:
                # Total tokens
                total_result = await session.execute(
                    select(func.sum(TokenUsageRow.total_tokens))
                    .where(TokenUsageRow.timestamp >= since)
                )
                total = total_result.scalar() or 0

                # By model
                model_result = await session.execute(
                    select(
                        TokenUsageRow.model,
                        func.sum(TokenUsageRow.total_tokens),
                    )
                    .where(TokenUsageRow.timestamp >= since)
                    .group_by(TokenUsageRow.model)
                )
                by_model = {row[0]: row[1] for row in model_result.all()}

                # By role
                role_result = await session.execute(
                    select(
                        TokenUsageRow.agent_role,
                        func.sum(TokenUsageRow.total_tokens),
                    )
                    .where(TokenUsageRow.timestamp >= since)
                    .group_by(TokenUsageRow.agent_role)
                )
                by_role = {row[0]: row[1] for row in role_result.all() if row[0]}

            return {
                "total_tokens": total,
                "by_model": by_model,
                "by_role": by_role,
                "period_days": days,
            }
        except Exception as e:
            logger.error("Failed to get token usage stats: %s", e)
            return {"total_tokens": self._total_tokens, "by_model": self._session_usage}


token_tracker = TokenTracker()
