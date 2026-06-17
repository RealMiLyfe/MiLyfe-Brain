"""
MiLyfe Brain - Batch Execution Tools

Parallel execution of multiple tool calls.
"""
from __future__ import annotations

import asyncio
import inspect
import json
import time
from typing import Any, Dict, List, TYPE_CHECKING

from config import settings
from models.schemas import PermissionLevel

if TYPE_CHECKING:
    from tools.registry import ToolRegistry


async def batch_execute(calls: List[Dict[str, Any]]) -> str:
    """Execute multiple tool calls in parallel.

    Args:
        calls: List of tool call dicts, each with 'tool' and 'arguments' keys.
            Example: [{"tool": "file_read", "arguments": {"path": "foo.txt"}}]

    Returns:
        JSON-formatted results for each call.
    """
    # Import here to avoid circular imports
    from tools.registry import tool_registry

    if not calls:
        return "Error: No tool calls provided"

    max_parallel = settings.max_batch_parallel
    if len(calls) > max_parallel:
        return f"Error: Maximum {max_parallel} parallel calls allowed, got {len(calls)}"

    # Validate all calls first
    for i, call in enumerate(calls):
        if not isinstance(call, dict):
            return f"Error: Call {i} must be a dict with 'tool' and 'arguments'"
        if "tool" not in call:
            return f"Error: Call {i} missing 'tool' key"
        tool_name = call["tool"]
        if tool_registry.get_tool(tool_name) is None:
            return f"Error: Call {i} references unknown tool '{tool_name}'"

    async def _execute_single(index: int, call: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single tool call."""
        tool_name = call["tool"]
        arguments = call.get("arguments", {})
        start = time.perf_counter()

        try:
            tool_info = tool_registry.get_tool(tool_name)
            if tool_info is None:
                return {
                    "index": index,
                    "tool": tool_name,
                    "success": False,
                    "error": f"Tool not found: {tool_name}",
                    "duration_ms": 0.0,
                }

            handler = tool_registry._tools[tool_name]["handler"]

            if inspect.iscoroutinefunction(handler):
                result = await handler(**arguments)
            else:
                result = handler(**arguments)

            duration = (time.perf_counter() - start) * 1000
            return {
                "index": index,
                "tool": tool_name,
                "success": True,
                "output": str(result),
                "duration_ms": round(duration, 2),
            }
        except Exception as e:
            duration = (time.perf_counter() - start) * 1000
            return {
                "index": index,
                "tool": tool_name,
                "success": False,
                "error": f"{type(e).__name__}: {e}",
                "duration_ms": round(duration, 2),
            }

    # Execute all calls in parallel
    tasks = [_execute_single(i, call) for i, call in enumerate(calls)]
    results = await asyncio.gather(*tasks, return_exceptions=False)

    # Sort by index to maintain order
    results_sorted = sorted(results, key=lambda r: r["index"])

    # Format output
    output_parts = [f"Batch execution ({len(results_sorted)} calls):"]
    success_count = sum(1 for r in results_sorted if r["success"])
    output_parts.append(f"  Success: {success_count}/{len(results_sorted)}")
    output_parts.append("")

    for r in results_sorted:
        status = "OK" if r["success"] else "FAIL"
        output_parts.append(f"[{r['index']}] {r['tool']} [{status}] ({r['duration_ms']:.1f}ms)")
        if r["success"]:
            output_text = r.get("output", "")
            if len(output_text) > 500:
                output_text = output_text[:500] + "..."
            output_parts.append(f"    {output_text}")
        else:
            output_parts.append(f"    Error: {r.get('error', 'unknown')}")

    return "\n".join(output_parts)


def register_batch_tools(registry: ToolRegistry) -> None:
    """Register batch execution tools with the tool registry."""
    registry.register(
        name="batch_execute",
        handler=batch_execute,
        category="batch",
        description="Execute multiple tool calls in parallel (max 10).",
        parameters={
            "calls": {
                "type": "array",
                "description": "List of {tool, arguments} dicts to execute in parallel",
                "required": True,
                "items": {
                    "type": "object",
                    "properties": {
                        "tool": {"type": "string"},
                        "arguments": {"type": "object"},
                    },
                },
            },
        },
        permission=PermissionLevel.MODERATE,
        returns="JSON-formatted results for each call with timing",
    )
