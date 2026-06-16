"""Token Tracker — Track token usage per agent/model/playbook."""

import uuid
from datetime import datetime
from typing import Optional

import structlog

logger = structlog.get_logger()


class TokenTracker:
    """Track LLM token usage."""

    async def track(
        self,
        prompt_tokens: int,
        completion_tokens: int,
        model: str,
        agent_id: Optional[str] = None,
        agent_role: Optional[str] = None,
        playbook_id: Optional[str] = None,
    ) -> None:
        """Record token usage."""
        from memory.database import db

        usage_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()

        try:
            await db.execute(
                """INSERT INTO token_usage
                   (id, agent_id, agent_role, model, playbook_id, prompt_tokens, completion_tokens, timestamp)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (usage_id, agent_id, agent_role, model, playbook_id, prompt_tokens, completion_tokens, now),
            )
        except Exception as e:
            logger.warning("Token tracking failed", error=str(e))

    async def get_total(self) -> dict:
        """Get total token usage."""
        from memory.database import db

        row = await db.fetch_one(
            "SELECT COALESCE(SUM(prompt_tokens),0) as p, COALESCE(SUM(completion_tokens),0) as c FROM token_usage"
        )
        if row:
            return {"prompt": row["p"], "completion": row["c"], "total": row["p"] + row["c"]}
        return {"prompt": 0, "completion": 0, "total": 0}


# Global instance
token_tracker = TokenTracker()
