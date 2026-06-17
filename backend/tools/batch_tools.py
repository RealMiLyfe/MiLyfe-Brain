"""Batch execution tools for MiLyfe Brain.

Provides parallel execution of multiple tool calls.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

MAX_PARALLEL_CALLS = 10


async def batch_execute(calls: List[Dict[str, Any]]) -> str:
    """Execute multiple tool calls in parallel.

    Args:
        calls: List of dicts, each with 'tool' (str) and 'arguments' (dict).
               Example: [{"tool": "file_read", "arguments": {"path": "README.md"}}]

    Returns:
        JSON-formatted string with results for each call.
    """
    # Import here to avoid circular imports
    from tools.registry import tool_registry

    if not calls:
        return "[ERROR] No calls provided to batch_execute."

    if len(calls) > MAX_PARALLEL_CALLS:
        return (
            f"[ERROR] Too many parallel calls: {len(calls)}. "
            f"Maximum is {MAX_PARALLEL_CALLS}."
        )

    # Validate call structure
    for i, call in enumerate(calls):
        if not isinstance(call, dict):
            return f"[ERROR] Call {i} is not a dict."
        if "tool" not in call:
            return f"[ERROR] Call {i} missing 'tool' field."
        if "arguments" not in call:
            return f"[ERROR] Call {i} missing 'arguments' field."

    async def _execute_single(index: int, call: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single tool call and capture result or error."""
        tool_name = call["tool"]
        arguments = call.get("arguments", {})

        try:
            result = await tool_registry.execute(
                tool_name, arguments, approved=True
            )
            return {"index": index, "tool": tool_name, "status": "success", "result": result}
        except Exception as exc:
            return {
                "index": index,
                "tool": tool_name,
                "status": "error",
                "error": f"{type(exc).__name__}: {exc}",
            }

    # Execute all calls in parallel
    tasks = [_execute_single(i, call) for i, call in enumerate(calls)]
    results = await asyncio.gather(*tasks, return_exceptions=False)

    # Sort by original index
    results_sorted = sorted(results, key=lambda r: r["index"])

    logger.info(
        "batch_execute: %d calls completed (%d success, %d errors)",
        len(results_sorted),
        sum(1 for r in results_sorted if r["status"] == "success"),
        sum(1 for r in results_sorted if r["status"] == "error"),
    )

    return json.dumps(results_sorted, indent=2, default=str)
