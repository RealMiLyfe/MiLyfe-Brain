"""Context Manager — Context window management and compaction."""

from typing import Optional

import structlog

from config import settings

logger = structlog.get_logger()


class ContextManager:
    """Manage LLM context window size and compaction."""

    def __init__(self):
        self.threshold = settings.context_summarize_threshold

    def estimate_tokens(self, messages: list[dict]) -> int:
        """Estimate token count from messages (rough: 4 chars ≈ 1 token)."""
        total_chars = sum(len(m.get("content", "")) for m in messages)
        return total_chars // 4

    def needs_compaction(self, messages: list[dict]) -> bool:
        """Check if messages exceed context threshold."""
        return self.estimate_tokens(messages) > self.threshold

    async def compact(self, messages: list[dict]) -> list[dict]:
        """Compact messages by summarizing older ones."""
        if not self.needs_compaction(messages):
            return messages

        # Keep system message and last N messages
        system_msg = messages[0] if messages and messages[0]["role"] == "system" else None
        recent_count = min(6, len(messages) // 2)
        recent = messages[-recent_count:]
        older = messages[1:-recent_count] if system_msg else messages[:-recent_count]

        if not older:
            return messages

        # Summarize older messages
        summary = self._rule_based_summary(older)

        result = []
        if system_msg:
            result.append(system_msg)
        result.append({"role": "system", "content": f"[Context Summary]\n{summary}"})
        result.extend(recent)

        logger.info("Context compacted",
                    original_tokens=self.estimate_tokens(messages),
                    compacted_tokens=self.estimate_tokens(result))
        return result

    def _rule_based_summary(self, messages: list[dict]) -> str:
        """Rule-based fallback for context summarization."""
        parts = []
        for msg in messages:
            content = msg.get("content", "")
            role = msg.get("role", "")
            # Keep first 100 chars of each message
            if content:
                parts.append(f"[{role}]: {content[:100]}...")

        return "\n".join(parts[-10:])  # Keep last 10 summarized


# Global instance
context_manager = ContextManager()
