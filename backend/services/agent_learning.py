"""
MiLyfe Brain - Agent Learning Service

Tracks agent performance outcomes including corrections, failure patterns,
and specializations. Enables agents to improve over time based on historical data.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Dict, List, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)

# In-memory learning store (supplemented by DB persistence)
_learning_store: Dict[str, List[Dict]] = {}


async def record_outcome(
    agent_role: str,
    task: str,
    result: str,
    duration_ms: float,
    success: bool,
    tokens_used: int,
    playbook_id: Optional[str] = None,
) -> None:
    """
    Record the outcome of an agent task execution.

    Tracks corrections, failure patterns, and specializations for
    continuous agent improvement.

    Args:
        agent_role: The role of the agent (e.g., 'coder', 'planner').
        task: Description of the task attempted.
        result: Result or output of the task.
        duration_ms: Execution duration in milliseconds.
        success: Whether the task succeeded.
        tokens_used: Total tokens consumed.
        playbook_id: Optional associated playbook ID.
    """
    record = {
        "id": str(uuid4()),
        "agent_role": agent_role,
        "task": task[:500],  # Truncate for storage
        "result_preview": result[:200] if result else "",
        "duration_ms": duration_ms,
        "success": success,
        "tokens_used": tokens_used,
        "playbook_id": playbook_id,
        "timestamp": datetime.utcnow().isoformat(),
    }

    # Store in memory grouped by role
    if agent_role not in _learning_store:
        _learning_store[agent_role] = []
    _learning_store[agent_role].append(record)

    # Keep only last 100 records per role
    if len(_learning_store[agent_role]) > 100:
        _learning_store[agent_role] = _learning_store[agent_role][-100:]

    # Persist to database
    try:
        from memory.database import ActionLogRow, async_session_factory

        if async_session_factory is not None:
            async with async_session_factory() as session:
                log_row = ActionLogRow(
                    id=record["id"],
                    playbook_id=playbook_id,
                    agent_role=agent_role,
                    action_type="task_execution",
                    description=task[:500],
                    details=f"success={success}, duration_ms={duration_ms}, tokens={tokens_used}",
                    risk_level="low",
                    success=success,
                    timestamp=datetime.utcnow(),
                )
                session.add(log_row)
                await session.commit()
    except Exception as e:
        logger.debug("Failed to persist learning record: %s", e)

    if not success:
        logger.info(
            "Agent learning: %s failed task (duration=%dms, tokens=%d): %s",
            agent_role, duration_ms, tokens_used, task[:100],
        )
    else:
        logger.debug(
            "Agent learning: %s completed task (duration=%dms, tokens=%d)",
            agent_role, duration_ms, tokens_used,
        )


def get_failure_patterns(agent_role: str) -> List[Dict]:
    """
    Get recent failure patterns for an agent role.

    Args:
        agent_role: The agent role to query.

    Returns:
        List of failure records.
    """
    records = _learning_store.get(agent_role, [])
    failures = [r for r in records if not r["success"]]
    return failures[-20:]  # Last 20 failures


def get_specializations(agent_role: str) -> Dict[str, float]:
    """
    Compute specialization scores based on success rates per task type.

    Args:
        agent_role: The agent role to analyze.

    Returns:
        Dict mapping task keywords to success rate (0.0 - 1.0).
    """
    records = _learning_store.get(agent_role, [])
    if not records:
        return {}

    # Simple keyword extraction from tasks
    keyword_stats: Dict[str, Dict[str, int]] = {}

    for record in records:
        task_words = record["task"].lower().split()[:5]  # First 5 words
        for word in task_words:
            if len(word) < 4:
                continue
            if word not in keyword_stats:
                keyword_stats[word] = {"success": 0, "total": 0}
            keyword_stats[word]["total"] += 1
            if record["success"]:
                keyword_stats[word]["success"] += 1

    # Compute success rates (only for keywords with enough data)
    specializations: Dict[str, float] = {}
    for keyword, stats in keyword_stats.items():
        if stats["total"] >= 3:
            specializations[keyword] = stats["success"] / stats["total"]

    return specializations


def get_average_performance(agent_role: str) -> Dict[str, float]:
    """
    Get average performance metrics for an agent role.

    Args:
        agent_role: The agent role to query.

    Returns:
        Dict with avg_duration_ms, success_rate, avg_tokens.
    """
    records = _learning_store.get(agent_role, [])
    if not records:
        return {"avg_duration_ms": 0.0, "success_rate": 0.0, "avg_tokens": 0.0}

    total = len(records)
    successes = sum(1 for r in records if r["success"])
    avg_duration = sum(r["duration_ms"] for r in records) / total
    avg_tokens = sum(r["tokens_used"] for r in records) / total

    return {
        "avg_duration_ms": avg_duration,
        "success_rate": successes / total,
        "avg_tokens": avg_tokens,
        "total_tasks": total,
    }
