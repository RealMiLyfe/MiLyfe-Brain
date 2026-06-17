"""MiLyfe Brain — Parallel Multi-Tool Batch Execution."""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List

from config import settings
from models.schemas import PermissionLevel


async def batch_execute(calls: List[Dict[str, Any]]) -> str:
    """Execute multiple tool calls in parallel.

    Each call: {"tool": "name", "args": {...}}
    Max 10 parallel calls per batch.
    """
    if not calls:
        return "No calls provided"

    if len(calls) > settings.max_batch_parallel:
        return f"Too many calls (max {settings.max_batch_parallel})"

    from tools.registry import tool_registry

    async def _run_one(call: dict) -> str:
        tool_name = call.get("tool", "")
        args = call.get("args", {})
        result = await tool_registry.execute(tool_name, args)
        if result.success:
            return f"[{tool_name}] OK: {result.output[:500]}"
        return f"[{tool_name}] FAILED: {result.error}"

    # Execute all in parallel
    tasks = [_run_one(c) for c in calls]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    output_parts = []
    for i, r in enumerate(results):
        if isinstance(r, Exception):
            output_parts.append(f"Call {i+1}: ERROR - {r}")
        else:
            output_parts.append(f"Call {i+1}: {r}")

    return "\n\n".join(output_parts)


def register_batch_tools(registry):
    """Register batch execution tools."""
    registry.register(
        name="batch_execute",
        handler=batch_execute,
        category="Batch",
        description="Execute multiple tools in parallel (max 10)",
        parameters={"calls": 'List[{"tool": str, "args": dict}]'},
        permission=PermissionLevel.NOTIFY,
    )
