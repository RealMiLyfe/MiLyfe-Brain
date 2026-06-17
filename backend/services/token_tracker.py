"""MiLyfe Brain — Token Usage Tracker."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

import structlog

logger = structlog.get_logger()


class TokenTracker:
    """Tracks token usage per agent/model/playbook."""

    async def record(
        self,
        agent_id: Optional[str] = None,
        agent_role: Optional[str] = None,
        model: str = "",
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        playbook_id: Optional[str] = None,
    ):
        """Record token usage."""
        try:
            from memory.database import TokenUsageRow, async_session_factory

            total = prompt_tokens + completion_tokens
            async with async_session_factory() as session:
                session.add(TokenUsageRow(
                    id=str(uuid.uuid4()),
                    agent_id=agent_id,
                    agent_role=agent_role,
                    model=model,
                    playbook_id=playbook_id,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=total,
                    timestamp=datetime.utcnow(),
                ))
                await session.commit()
        except Exception as e:
            logger.debug("token_tracking_failed", error=str(e))


# Singleton
token_tracker = TokenTracker()
