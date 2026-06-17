"""Token Tracker — LLM token usage tracking and statistics.

Records per-call token usage and provides aggregated statistics
by model, role, and daily breakdown.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from memory.database import async_session_factory, TokenUsageModel

logger = logging.getLogger(__name__)


class TokenTracker:
    """Tracks LLM token consumption across agents and models.

    Provides:
    - Per-call recording with agent/model metadata
    - Aggregated statistics over configurable time windows
    - Breakdown by model, role, and day
    """

    async def record(
        self,
        agent_id: str,
        agent_role: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        playbook_id: Optional[str] = None,
    ) -> None:
        """Record a token usage entry.

        Args:
            agent_id: The agent that made the LLM call.
            agent_role: The agent's role.
            model: The model used.
            prompt_tokens: Number of prompt/input tokens.
            completion_tokens: Number of completion/output tokens.
            playbook_id: Optional associated playbook ID.
        """
        async with async_session_factory() as db:
            entry = TokenUsageModel(
                id=str(uuid.uuid4()),
                agent_id=agent_id,
                agent_role=agent_role,
                model=model,
                playbook_id=playbook_id,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                timestamp=datetime.utcnow(),
            )
            db.add(entry)
            await db.commit()

    async def get_stats(self, days: int = 7) -> dict:
        """Get aggregated token usage statistics.

        Args:
            days: Number of days to look back (default 7).

        Returns:
            Dict with totals, per-model breakdown, per-role breakdown,
            and daily breakdown.
        """
        since = datetime.utcnow() - timedelta(days=days)

        async with async_session_factory() as db:
            # Total usage
            total_result = await db.execute(
                select(
                    func.sum(TokenUsageModel.prompt_tokens),
                    func.sum(TokenUsageModel.completion_tokens),
                    func.count(TokenUsageModel.id),
                ).where(TokenUsageModel.timestamp >= since)
            )
            row = total_result.one()
            total_prompt = row[0] or 0
            total_completion = row[1] or 0
            total_calls = row[2] or 0

            # By model
            model_result = await db.execute(
                select(
                    TokenUsageModel.model,
                    func.sum(TokenUsageModel.prompt_tokens),
                    func.sum(TokenUsageModel.completion_tokens),
                    func.count(TokenUsageModel.id),
                )
                .where(TokenUsageModel.timestamp >= since)
                .group_by(TokenUsageModel.model)
            )
            by_model = {
                row[0]: {
                    "prompt_tokens": row[1] or 0,
                    "completion_tokens": row[2] or 0,
                    "calls": row[3] or 0,
                }
                for row in model_result.all()
            }

            # By role
            role_result = await db.execute(
                select(
                    TokenUsageModel.agent_role,
                    func.sum(TokenUsageModel.prompt_tokens),
                    func.sum(TokenUsageModel.completion_tokens),
                    func.count(TokenUsageModel.id),
                )
                .where(TokenUsageModel.timestamp >= since)
                .group_by(TokenUsageModel.agent_role)
            )
            by_role = {
                (row[0] or "unknown"): {
                    "prompt_tokens": row[1] or 0,
                    "completion_tokens": row[2] or 0,
                    "calls": row[3] or 0,
                }
                for row in role_result.all()
            }

        return {
            "period_days": days,
            "totals": {
                "prompt_tokens": total_prompt,
                "completion_tokens": total_completion,
                "total_tokens": total_prompt + total_completion,
                "calls": total_calls,
            },
            "by_model": by_model,
            "by_role": by_role,
        }


# Singleton
token_tracker = TokenTracker()



# Convenience function for inline usage (avoids importing the class)
async def track_usage(
    agent_id: str,
    agent_role: str,
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    playbook_id: Optional[str] = None,
) -> None:
    """Record token usage — convenience wrapper around TokenTracker.record()."""
    await token_tracker.record(
        agent_id=agent_id,
        agent_role=agent_role,
        model=model,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        playbook_id=playbook_id,
    )
