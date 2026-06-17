"""Token usage statistics routes."""

from fastapi import APIRouter

from models.schemas import TokenStats

router = APIRouter()


@router.get("/stats", response_model=TokenStats)
async def get_token_stats():
    """Get token usage statistics."""
    from memory.database import db

    # Total tokens
    totals = await db.fetch_one(
        """SELECT COALESCE(SUM(prompt_tokens), 0) as total_prompt,
                  COALESCE(SUM(completion_tokens), 0) as total_completion
           FROM token_usage"""
    )

    # By model
    by_model_rows = await db.fetch_all(
        """SELECT model, SUM(prompt_tokens) as prompt, SUM(completion_tokens) as completion
           FROM token_usage GROUP BY model"""
    )

    # By role
    by_role_rows = await db.fetch_all(
        """SELECT agent_role, SUM(prompt_tokens) as prompt, SUM(completion_tokens) as completion
           FROM token_usage GROUP BY agent_role"""
    )

    by_model = {
        row["model"]: {"prompt_tokens": row["prompt"], "completion_tokens": row["completion"]}
        for row in by_model_rows
    }

    by_role = {
        row["agent_role"]: {"prompt_tokens": row["prompt"], "completion_tokens": row["completion"]}
        for row in by_role_rows
        if row["agent_role"]
    }

    total_prompt = totals["total_prompt"] if totals else 0
    total_completion = totals["total_completion"] if totals else 0

    return TokenStats(
        total_prompt_tokens=total_prompt,
        total_completion_tokens=total_completion,
        total_tokens=total_prompt + total_completion,
        by_model=by_model,
        by_role=by_role,
    )


@router.get("/history")
async def get_token_history(days: int = 7):
    """Get token usage history by day."""
    from memory.database import db

    rows = await db.fetch_all(
        """SELECT DATE(timestamp) as date,
                  SUM(prompt_tokens) as prompt,
                  SUM(completion_tokens) as completion
           FROM token_usage
           WHERE timestamp >= datetime('now', ? || ' days')
           GROUP BY DATE(timestamp)
           ORDER BY date""",
        (f"-{days}",),
    )

    return [
        {
            "date": row["date"],
            "prompt_tokens": row["prompt"],
            "completion_tokens": row["completion"],
            "total": row["prompt"] + row["completion"],
        }
        for row in rows
    ]
