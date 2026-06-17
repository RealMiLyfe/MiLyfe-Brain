"""Context Manager — Token threshold checking and message compaction.

Manages context windows to prevent exceeding model token limits.
"""

from __future__ import annotations

import logging
from typing import Dict, List

import httpx

from config import settings

logger = logging.getLogger(__name__)


class ContextManager:
    """Manages context window sizes for agent conversations.

    Features:
    - Check if messages exceed the token threshold
    - Compact old messages by summarizing them
    - Estimate token count from text (rough: len/4)
    """

    def __init__(self, threshold: int = settings.context_summarize_threshold) -> None:
        self._threshold = threshold

    def check_threshold(self, messages: List[Dict[str, str]]) -> bool:
        """Check if messages exceed the token threshold.

        Args:
            messages: List of message dicts with 'content' key.

        Returns:
            True if estimated tokens exceed the threshold.
        """
        total = sum(self.estimate_tokens(m.get("content", "")) for m in messages)
        return total > self._threshold

    async def compact(self, messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Summarize old messages to reduce context size.

        Keeps the system prompt and last few messages intact.
        Summarizes everything in between into a single summary message.

        Args:
            messages: Full list of conversation messages.

        Returns:
            Compacted message list.
        """
        if len(messages) <= 4:
            return messages

        # Keep system prompt (first) and last 3 messages
        system_msg = messages[0] if messages[0].get("role") == "system" else None
        recent = messages[-3:]
        middle = messages[1:-3] if system_msg else messages[:-3]

        if not middle:
            return messages

        # Build summary of middle messages
        middle_text = "\n".join(
            f"{m.get('role', 'unknown')}: {m.get('content', '')[:200]}"
            for m in middle
        )

        # Try to summarize via Ollama
        summary = await self._summarize(middle_text)

        result = []
        if system_msg:
            result.append(system_msg)
        result.append({
            "role": "system",
            "content": f"[Previous conversation summary: {summary}]",
        })
        result.extend(recent)

        return result

    def estimate_tokens(self, text: str) -> int:
        """Rough token estimation (approximately 1 token per 4 characters).

        Args:
            text: The text to estimate tokens for.

        Returns:
            Estimated token count.
        """
        return max(1, len(text) // 4)

    async def _summarize(self, text: str) -> str:
        """Summarize text using Ollama."""
        try:
            async with httpx.AsyncClient(
                base_url=settings.ollama_base_url,
                timeout=httpx.Timeout(connect=5.0, read=30.0, write=5.0, pool=5.0),
            ) as client:
                response = await client.post(
                    "/api/generate",
                    json={
                        "model": settings.default_light_model,
                        "prompt": (
                            "Summarize the following conversation in 2-3 sentences, "
                            "preserving key decisions and context:\n\n"
                            f"{text[:3000]}"
                        ),
                        "stream": False,
                        "options": {"temperature": 0.3, "num_predict": 256},
                    },
                )
                response.raise_for_status()
                return response.json().get("response", "Previous conversation context.")
        except Exception as e:
            logger.warning("Summarization failed: %s", e)
            return f"Previous conversation ({len(text)} chars of context)"


# Singleton
context_manager = ContextManager()
