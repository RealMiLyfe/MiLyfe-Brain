"""
MiLyfe Brain - Compliance Service

Provides data compliance capabilities including PII scanning,
license detection, data lineage tracking, and retention policy enforcement.
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# PII detection patterns
_PII_PATTERNS = {
    "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),
    "phone_us": re.compile(r"\b(\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"),
    "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "credit_card": re.compile(r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b"),
    "ip_address": re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b"),
}

# License patterns
_LICENSE_PATTERNS = {
    "MIT": re.compile(r"MIT License|Permission is hereby granted, free of charge", re.IGNORECASE),
    "Apache-2.0": re.compile(r"Apache License.*Version 2\.0|Licensed under the Apache License", re.IGNORECASE),
    "GPL-3.0": re.compile(r"GNU GENERAL PUBLIC LICENSE.*Version 3|GPL-3\.0", re.IGNORECASE),
    "BSD-3-Clause": re.compile(r"BSD 3-Clause|Redistribution and use in source and binary forms", re.IGNORECASE),
    "ISC": re.compile(r"ISC License|Permission to use, copy, modify", re.IGNORECASE),
}


async def scan_for_pii(text: str) -> Dict[str, Any]:
    """
    Scan text content for personally identifiable information.

    Args:
        text: Text content to scan.

    Returns:
        Dict with 'found' (bool), 'types' (list of PII types found),
        'count' (total matches), 'details' (per-type match count).
    """
    if not text:
        return {"found": False, "types": [], "count": 0, "details": {}}

    found_types: List[str] = []
    details: Dict[str, int] = {}
    total_count = 0

    for pii_type, pattern in _PII_PATTERNS.items():
        matches = pattern.findall(text)
        if matches:
            found_types.append(pii_type)
            details[pii_type] = len(matches)
            total_count += len(matches)

    result = {
        "found": total_count > 0,
        "types": found_types,
        "count": total_count,
        "details": details,
    }

    if total_count > 0:
        logger.warning("PII detected: %d instance(s) of types %s", total_count, found_types)

    return result


async def detect_license(content: str) -> Dict[str, Any]:
    """
    Detect software license in text content.

    Args:
        content: File content to analyze.

    Returns:
        Dict with 'detected' (bool), 'license' (name or None), 'confidence'.
    """
    if not content:
        return {"detected": False, "license": None, "confidence": 0.0}

    for license_name, pattern in _LICENSE_PATTERNS.items():
        if pattern.search(content):
            return {
                "detected": True,
                "license": license_name,
                "confidence": 0.85,
            }

    return {"detected": False, "license": None, "confidence": 0.0}


async def get_data_lineage(playbook_id: str) -> Dict[str, Any]:
    """
    Get data lineage for a playbook execution.

    Tracks what data was read, transformed, and written.

    Args:
        playbook_id: ID of the playbook.

    Returns:
        Dict with 'inputs', 'transformations', 'outputs'.
    """
    lineage: Dict[str, Any] = {
        "playbook_id": playbook_id,
        "inputs": [],
        "transformations": [],
        "outputs": [],
        "generated_at": datetime.utcnow().isoformat(),
    }

    try:
        from sqlalchemy import select

        from memory.database import ActionLogRow, async_session_factory

        if async_session_factory is None:
            return lineage

        async with async_session_factory() as session:
            result = await session.execute(
                select(ActionLogRow)
                .where(ActionLogRow.playbook_id == playbook_id)
                .order_by(ActionLogRow.timestamp)
            )
            actions = result.scalars().all()

        for action in actions:
            entry = {
                "action_type": action.action_type,
                "description": action.description[:200],
                "timestamp": action.timestamp.isoformat() if action.timestamp else None,
            }

            if action.action_type in ("file_read", "memory_recall", "search"):
                lineage["inputs"].append(entry)
            elif action.action_type in ("file_write", "file_delete", "memory_store"):
                lineage["outputs"].append(entry)
            else:
                lineage["transformations"].append(entry)

    except Exception as e:
        logger.error("Failed to get data lineage: %s", e)

    return lineage


async def apply_retention_policy(
    max_age_days: int = 90,
    dry_run: bool = True,
) -> Dict[str, Any]:
    """
    Apply data retention policy by removing old records.

    Args:
        max_age_days: Maximum age of records to keep.
        dry_run: If True, only count records without deleting.

    Returns:
        Dict with 'records_affected', 'dry_run', 'tables'.
    """
    cutoff = datetime.utcnow() - timedelta(days=max_age_days)
    result: Dict[str, Any] = {
        "dry_run": dry_run,
        "max_age_days": max_age_days,
        "cutoff_date": cutoff.isoformat(),
        "tables": {},
        "total_records_affected": 0,
    }

    try:
        from sqlalchemy import delete, func, select

        from memory.database import (
            ActionLogRow,
            ChatMessageRow,
            NotificationRow,
            TokenUsageRow,
            async_session_factory,
        )

        if async_session_factory is None:
            return result

        tables_to_clean = [
            ("action_logs", ActionLogRow, ActionLogRow.timestamp),
            ("token_usage", TokenUsageRow, TokenUsageRow.timestamp),
            ("notifications", NotificationRow, NotificationRow.created_at),
            ("chat_messages", ChatMessageRow, ChatMessageRow.timestamp),
        ]

        async with async_session_factory() as session:
            for table_name, model, time_col in tables_to_clean:
                count_result = await session.execute(
                    select(func.count()).where(time_col < cutoff)
                )
                count = count_result.scalar() or 0
                result["tables"][table_name] = count
                result["total_records_affected"] += count

                if not dry_run and count > 0:
                    await session.execute(
                        delete(model).where(time_col < cutoff)
                    )

            if not dry_run:
                await session.commit()

    except Exception as e:
        logger.error("Failed to apply retention policy: %s", e)
        result["error"] = str(e)

    logger.info(
        "Retention policy %s: %d records affected",
        "checked (dry run)" if dry_run else "applied",
        result["total_records_affected"],
    )
    return result
