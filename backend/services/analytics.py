"""MiLyfe Brain — Analytics Dashboard Service.

Agent performance, playbook success rates, resource utilization, cost equivalency.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, List

import structlog
from sqlalchemy import select, func

logger = structlog.get_logger()


class AnalyticsService:
    """Provides intelligence about system performance and value."""

    async def get_overview(self, days: int = 30) -> Dict:
        """Get analytics overview for the last N days."""
        from memory.database import (
            ActionLogRow, PlaybookRow, TokenUsageRow,
            async_session_factory,
        )

        cutoff = datetime.utcnow() - timedelta(days=days)

        async with async_session_factory() as session:
            # Playbook stats
            pb_total = (await session.execute(
                select(func.count(PlaybookRow.id)).where(PlaybookRow.created_at >= cutoff)
            )).scalar() or 0

            pb_completed = (await session.execute(
                select(func.count(PlaybookRow.id))
                .where(PlaybookRow.status == "completed")
                .where(PlaybookRow.created_at >= cutoff)
            )).scalar() or 0

            pb_failed = (await session.execute(
                select(func.count(PlaybookRow.id))
                .where(PlaybookRow.status == "failed")
                .where(PlaybookRow.created_at >= cutoff)
            )).scalar() or 0

            # Token stats
            total_tokens = (await session.execute(
                select(func.sum(TokenUsageRow.total_tokens))
                .where(TokenUsageRow.timestamp >= cutoff)
            )).scalar() or 0

            # Actions
            total_actions = (await session.execute(
                select(func.count(ActionLogRow.id))
                .where(ActionLogRow.timestamp >= cutoff)
            )).scalar() or 0

            # By role performance
            role_stats = (await session.execute(
                select(
                    ActionLogRow.agent_role,
                    func.count(ActionLogRow.id),
                )
                .where(ActionLogRow.timestamp >= cutoff)
                .group_by(ActionLogRow.agent_role)
            )).all()

            # Token by model
            model_stats = (await session.execute(
                select(
                    TokenUsageRow.model,
                    func.sum(TokenUsageRow.total_tokens),
                )
                .where(TokenUsageRow.timestamp >= cutoff)
                .group_by(TokenUsageRow.model)
            )).all()

        # Cost equivalency calculations
        cost_gpt4 = (total_tokens / 1000) * 0.03
        cost_gpt35 = (total_tokens / 1000) * 0.002
        cost_claude = (total_tokens / 1000) * 0.015

        return {
            "period_days": days,
            "playbooks": {
                "total": pb_total,
                "completed": pb_completed,
                "failed": pb_failed,
                "success_rate": round(pb_completed / pb_total * 100, 1) if pb_total > 0 else 0,
            },
            "tokens": {
                "total": total_tokens,
                "by_model": {r[0]: r[1] for r in model_stats if r[0]},
            },
            "actions": {
                "total": total_actions,
                "by_role": {r[0]: r[1] for r in role_stats if r[0]},
            },
            "cost_savings": {
                "gpt4_equivalent_usd": round(cost_gpt4, 2),
                "gpt35_equivalent_usd": round(cost_gpt35, 2),
                "claude_equivalent_usd": round(cost_claude, 2),
                "actual_cost_usd": 0.0,
                "saved_usd": round(cost_gpt4, 2),
            },
            "generated_at": datetime.utcnow().isoformat(),
        }

    async def get_agent_performance(self) -> List[Dict]:
        """Get per-agent performance metrics."""
        from memory.database import ActionLogRow, PlaybookStepRow, async_session_factory

        async with async_session_factory() as session:
            # Steps by role and status
            result = await session.execute(
                select(
                    PlaybookStepRow.agent_role,
                    PlaybookStepRow.status,
                    func.count(PlaybookStepRow.id),
                )
                .group_by(PlaybookStepRow.agent_role, PlaybookStepRow.status)
            )
            rows = result.all()

        # Aggregate
        role_data: Dict[str, Dict] = {}
        for role, status, count in rows:
            if not role:
                continue
            if role not in role_data:
                role_data[role] = {"total": 0, "completed": 0, "failed": 0}
            role_data[role]["total"] += count
            if status == "completed":
                role_data[role]["completed"] += count
            elif status == "failed":
                role_data[role]["failed"] += count

        return [
            {
                "role": role,
                "total_tasks": data["total"],
                "completed": data["completed"],
                "failed": data["failed"],
                "success_rate": round(data["completed"] / data["total"] * 100, 1) if data["total"] > 0 else 0,
            }
            for role, data in role_data.items()
        ]


# Singleton
analytics_service = AnalyticsService()
