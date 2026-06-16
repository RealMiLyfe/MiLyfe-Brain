"""Quality Compaction — Heavy-model context summarization."""

from typing import Optional

import httpx
import structlog

from config import settings

logger = structlog.get_logger()


class QualityCompaction:
    """Use heavy model for high-quality context compaction."""

    COMPACTION_PROMPT = """Summarize the following conversation into a structured format:

1. KEY DECISIONS made
2. FILES modified or discussed
3. CURRENT STATE of the task
4. NEXT STEPS planned
5. BLOCKERS identified
6. KEY CONTEXT that must be preserved

Be concise but preserve all actionable information."""

    async def compact(self, messages: list[dict]) -> Optional[str]:
        """Compact messages using the heavy model."""
        # Build conversation text
        conversation = "\n".join(
            f"[{m['role']}]: {m['content'][:500]}" for m in messages if m.get("content")
        )

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(
                    f"{settings.ollama_base_url}/api/chat",
                    json={
                        "model": settings.default_heavy_model,
                        "messages": [
                            {"role": "system", "content": self.COMPACTION_PROMPT},
                            {"role": "user", "content": conversation},
                        ],
                        "stream": False,
                        "options": {"temperature": 0.3},
                    },
                )
                if resp.status_code == 200:
                    return resp.json().get("message", {}).get("content", "")
        except Exception as e:
            logger.warning("Quality compaction failed, using rule-based", error=str(e))

        # Fallback: rule-based
        return self._rule_based_fallback(messages)

    def _rule_based_fallback(self, messages: list[dict]) -> str:
        """Rule-based fallback when LLM is unavailable."""
        parts = []
        for msg in messages[-10:]:
            content = msg.get("content", "")
            if content:
                parts.append(f"[{msg['role']}]: {content[:150]}...")
        return "\n".join(parts)


# Global instance
quality_compaction = QualityCompaction()
