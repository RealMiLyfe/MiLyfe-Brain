"""Daily Digest — Morning summary generation."""

from datetime import datetime, timedelta

import structlog

from models.schemas import DigestResponse

logger = structlog.get_logger()


class DailyDigestService:
    """Generate daily activity digest."""

    async def generate(self) -> DigestResponse:
        """Generate today's digest."""
        from memory.database import db

        today = datetime.utcnow().date().isoformat()
        yesterday = (datetime.utcnow() - timedelta(days=1)).isoformat()

        # Get stats
        playbooks_run = await db.fetch_one(
            "SELECT COUNT(*) as c FROM playbooks WHERE created_at >= ?", (yesterday,)
        )
        actions_logged = await db.fetch_one(
            "SELECT COUNT(*) as c FROM action_logs WHERE timestamp >= ?", (yesterday,)
        )
        tokens_used = await db.fetch_one(
            "SELECT COALESCE(SUM(prompt_tokens + completion_tokens), 0) as t FROM token_usage WHERE timestamp >= ?",
            (yesterday,),
        )

        stats = {
            "playbooks_run": playbooks_run["c"] if playbooks_run else 0,
            "actions_logged": actions_logged["c"] if actions_logged else 0,
            "tokens_used": tokens_used["t"] if tokens_used else 0,
        }

        highlights = []
        if stats["playbooks_run"] > 0:
            highlights.append(f"{stats['playbooks_run']} playbook(s) executed")
        if stats["actions_logged"] > 0:
            highlights.append(f"{stats['actions_logged']} actions performed")
        if stats["tokens_used"] > 0:
            highlights.append(f"{stats['tokens_used']:,} tokens consumed")

        summary = f"Daily digest for {today}: " + ", ".join(highlights) if highlights else "No activity recorded."

        return DigestResponse(
            date=today,
            summary=summary,
            highlights=highlights,
            stats=stats,
        )


# Global instance
daily_digest_service = DailyDigestService()
