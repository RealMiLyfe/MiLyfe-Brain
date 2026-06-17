"""
MiLyfe Brain - Analytics Service

Provides aggregated analytics: overview stats, agent performance metrics,
and time-series data. Queries the database for reporting.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class AnalyticsService:
    """Aggregates and serves analytics data from the database."""

    def __init__(self) -> None:
        pass

    async def get_overview(self, days: int = 30) -> Dict[str, Any]:
        """
        Get a high-level overview of system activity.

        Args:
            days: Number of days to look back.

        Returns:
            Dict with playbook counts, token totals, success rates, etc.
        """
        since = datetime.utcnow() - timedelta(days=days)

        overview: Dict[str, Any] = {
            "period_days": days,
            "total_playbooks": 0,
            "completed_playbooks": 0,
            "failed_playbooks": 0,
            "total_tokens": 0,
            "total_actions": 0,
            "success_rate": 0.0,
            "avg_tokens_per_playbook": 0.0,
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
                return overview

            async with async_session_factory() as session:
                # Playbook stats
                pb_result = await session.execute(
                    select(
                        func.count(PlaybookRow.id),
                        func.sum(
                            func.cast(
                                PlaybookRow.status == "completed", type_=None
                            )
                        ),
                    )
                    .where(PlaybookRow.created_at >= since)
                )
                row = pb_result.one_or_none()

                # Simpler queries for counts
                total_pb = await session.execute(
                    select(func.count(PlaybookRow.id))
                    .where(PlaybookRow.created_at >= since)
                )
                overview["total_playbooks"] = total_pb.scalar() or 0

                completed_pb = await session.execute(
                    select(func.count(PlaybookRow.id))
                    .where(PlaybookRow.created_at >= since)
                    .where(PlaybookRow.status == "completed")
                )
                overview["completed_playbooks"] = completed_pb.scalar() or 0

                failed_pb = await session.execute(
                    select(func.count(PlaybookRow.id))
                    .where(PlaybookRow.created_at >= since)
                    .where(PlaybookRow.status == "failed")
                )
                overview["failed_playbooks"] = failed_pb.scalar() or 0

                # Token stats
                token_result = await session.execute(
                    select(func.sum(TokenUsageRow.total_tokens))
                    .where(TokenUsageRow.timestamp >= since)
                )
                overview["total_tokens"] = token_result.scalar() or 0

                # Action count
                action_result = await session.execute(
                    select(func.count(ActionLogRow.id))
                    .where(ActionLogRow.timestamp >= since)
                )
                overview["total_actions"] = action_result.scalar() or 0

            # Computed metrics
            if overview["total_playbooks"] > 0:
                overview["success_rate"] = (
                    overview["completed_playbooks"] / overview["total_playbooks"]
                )
                overview["avg_tokens_per_playbook"] = (
                    overview["total_tokens"] / overview["total_playbooks"]
                )

        except Exception as e:
            logger.error("Failed to get analytics overview: %s", e)

        return overview

    async def get_agent_performance(self) -> List[Dict[str, Any]]:
        """
        Get performance metrics per agent role.

        Returns:
            List of dicts with role, task_count, success_rate, avg_duration.
        """
        performance: List[Dict[str, Any]] = []

        try:
            from sqlalchemy import func, select

            from memory.database import ActionLogRow, async_session_factory

            if async_session_factory is None:
                return performance

            async with async_session_factory() as session:
                # Group by agent_role
                result = await session.execute(
                    select(
                        ActionLogRow.agent_role,
                        func.count(ActionLogRow.id),
                        func.sum(func.cast(ActionLogRow.success == True, type_=None)),  # noqa: E712
                    )
                    .where(ActionLogRow.agent_role.isnot(None))
                    .group_by(ActionLogRow.agent_role)
                )
                rows = result.all()

                for row in rows:
                    role = row[0]
                    total = row[1] or 0
                    successes = row[2] or 0
                    success_rate = successes / total if total > 0 else 0.0

                    performance.append({
                        "agent_role": role,
                        "task_count": total,
                        "success_count": successes,
                        "success_rate": round(success_rate, 3),
                    })

        except Exception as e:
            logger.error("Failed to get agent performance: %s", e)

        return performance

    async def get_token_timeline(self, days: int = 7) -> List[Dict[str, Any]]:
        """
        Get daily token usage for the last N days.

        Args:
            days: Number of days to include.

        Returns:
            List of dicts with date and token_count.
        """
        timeline: List[Dict[str, Any]] = []

        try:
            from sqlalchemy import func, select

            from memory.database import TokenUsageRow, async_session_factory

            if async_session_factory is None:
                return timeline

            since = datetime.utcnow() - timedelta(days=days)

            async with async_session_factory() as session:
                result = await session.execute(
                    select(
                        func.date(TokenUsageRow.timestamp),
                        func.sum(TokenUsageRow.total_tokens),
                    )
                    .where(TokenUsageRow.timestamp >= since)
                    .group_by(func.date(TokenUsageRow.timestamp))
                    .order_by(func.date(TokenUsageRow.timestamp))
                )
                rows = result.all()

                for row in rows:
                    timeline.append({
                        "date": str(row[0]),
                        "total_tokens": row[1] or 0,
                    })

        except Exception as e:
            logger.error("Failed to get token timeline: %s", e)

        return timeline


analytics_service = AnalyticsService()
