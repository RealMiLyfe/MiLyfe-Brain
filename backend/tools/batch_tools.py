"""Batch Tools — Parallel multi-tool execution."""

import asyncio
from typing import Any


async def batch_execute(calls: list[dict]) -> str:
    """Execute multiple tool calls in parallel.

    Args:
        calls: List of {"tool": "name", "params": {...}} objects
        Max 10 parallel calls.
    """
    from tools.registry import tool_registry

    if not calls:
        return "No tool calls provided"

    if len(calls) > 10:
        return "Maximum 10 parallel calls allowed"

    async def run_single(call: dict) -> dict:
        tool_name = call.get("tool", "")
        params = call.get("params", {})
        try:
            result = await tool_registry.execute(tool_name, params)
            return {"tool": tool_name, "success": True, "result": str(result)[:2000]}
        except Exception as e:
            return {"tool": tool_name, "success": False, "error": str(e)}

    results = await asyncio.gather(*[run_single(call) for call in calls])

    output_parts = []
    for r in results:
        status = "OK" if r["success"] else "FAILED"
        content = r.get("result", r.get("error", ""))
        output_parts.append(f"[{status}] {r['tool']}: {content[:500]}")

    return "\n\n".join(output_parts)


def register_batch_tools(registry):
    """Register batch tools with the tool registry."""
    registry.register("batch_execute", "Execute multiple tools in parallel", batch_execute, permission="notify",
                      params={"calls": "List of {tool, params} objects (max 10)"})
