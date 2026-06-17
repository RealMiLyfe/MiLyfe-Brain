"""MiLyfe Brain — Context Window Management."""

from __future__ import annotations

from typing import Dict, List

import structlog

from config import settings

logger = structlog.get_logger()


class ContextManager:
    """Manages context window size and triggers summarization."""

    def __init__(self):
        self.threshold = settings.context_summarize_threshold

    def estimate_tokens(self, messages: List[Dict[str, str]]) -> int:
        """Estimate token count (rough: 4 chars ≈ 1 token)."""
        total_chars = sum(len(m.get("content", "")) for m in messages)
        return total_chars // 4

    def needs_compaction(self, messages: List[Dict[str, str]]) -> bool:
        """Check if messages need compaction."""
        return self.estimate_tokens(messages) > self.threshold

    async def compact(self, messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Compact messages by summarizing older ones."""
        if not self.needs_compaction(messages):
            return messages

        # Keep system prompt and last N messages
        system_msgs = [m for m in messages if m["role"] == "system"]
        other_msgs = [m for m in messages if m["role"] != "system"]

        # Keep last 6 messages as-is
        keep_count = 6
        to_summarize = other_msgs[:-keep_count] if len(other_msgs) > keep_count else []
        to_keep = other_msgs[-keep_count:] if len(other_msgs) > keep_count else other_msgs

        if not to_summarize:
            return messages

        # Summarize older messages
        summary = await self._summarize(to_summarize)

        # Rebuild context
        result = system_msgs + [
            {"role": "system", "content": f"[Context summary of earlier conversation]\n{summary}"}
        ] + to_keep

        logger.info("context_compacted",
                    original_msgs=len(messages),
                    new_msgs=len(result),
                    saved_tokens=self.estimate_tokens(messages) - self.estimate_tokens(result))

        return result

    async def _summarize(self, messages: List[Dict[str, str]]) -> str:
        """Summarize messages using LLM (or fallback to rule-based)."""
        try:
            from services.quality_compaction import quality_compact
            return await quality_compact(messages)
        except Exception:
            return self._rule_based_summary(messages)

    def _rule_based_summary(self, messages: List[Dict[str, str]]) -> str:
        """Fallback rule-based summarization."""
        parts = []
        for m in messages:
            role = m.get("role", "")
            content = m.get("content", "")
            if role == "user":
                parts.append(f"- User asked: {content[:100]}")
            elif role == "assistant":
                parts.append(f"- Assistant: {content[:100]}")
        return "\n".join(parts[-20:])  # Last 20 entries


# Singleton
context_manager = ContextManager()
