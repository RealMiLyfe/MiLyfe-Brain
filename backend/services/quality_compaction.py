"""MiLyfe Brain — Quality Compaction (Heavy-model context summarization)."""

from __future__ import annotations

from typing import Dict, List

import structlog

from config import settings

logger = structlog.get_logger()

COMPACTION_PROMPT = """Summarize the following conversation into a structured format.
Preserve: decisions made, files modified, current state, next steps, blockers, and key context.
Be concise but don't lose important details.

Output format:
DECISIONS: (key decisions made)
FILES: (files created/modified)
STATE: (current project state)
NEXT_STEPS: (what needs to happen next)
BLOCKERS: (any issues or blockers)
KEY_CONTEXT: (important context to preserve)"""


async def quality_compact(messages: List[Dict[str, str]]) -> str:
    """Use heavy model to summarize conversation context."""
    # Build content to summarize
    content_parts = []
    for m in messages:
        role = m.get("role", "unknown")
        text = m.get("content", "")[:500]
        content_parts.append(f"[{role}]: {text}")

    conversation_text = "\n".join(content_parts)

    try:
        from tools.llm_client import call_ollama

        result = await call_ollama(
            messages=[
                {"role": "system", "content": COMPACTION_PROMPT},
                {"role": "user", "content": conversation_text},
            ],
            model=settings.default_heavy_model,
            temperature=0.3,
            max_tokens=1000,
        )

        summary = result.get("content", "")
        if summary:
            logger.info("quality_compaction_done", summary_len=len(summary))
            return summary

    except Exception as e:
        logger.warning("quality_compaction_failed", error=str(e))

    # Fallback: simple truncation
    return _rule_based_compact(messages)


def _rule_based_compact(messages: List[Dict[str, str]]) -> str:
    """Fallback rule-based compaction."""
    parts = ["[Compacted context]"]
    for m in messages[-10:]:
        role = m.get("role", "")
        content = m.get("content", "")[:150]
        if role in ("user", "assistant"):
            parts.append(f"- {role}: {content}")
    return "\n".join(parts)
