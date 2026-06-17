"""
MiLyfe Brain - Context Manager Service

Manages LLM context windows: estimates tokens, detects when compaction
is needed, and compacts messages using LLM summarization or rule-based
truncation as fallback.
"""
from __future__ import annotations

import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Rough token estimation: ~4 chars per token for English text
_CHARS_PER_TOKEN = 4


class ContextManager:
    """Manages LLM context window sizing and compaction."""

    def __init__(self) -> None:
        self._compaction_threshold: int = 32000  # tokens

    def estimate_tokens(self, messages: List[Dict[str, str]]) -> int:
        """
        Estimate token count for a list of messages.

        Uses a character-based heuristic: ~4 characters per token.
        Each message also has ~4 tokens overhead for role/formatting.

        Args:
            messages: List of message dicts with 'role' and 'content'.

        Returns:
            Estimated total token count.
        """
        total_chars = 0
        overhead_per_message = 4  # tokens for role, formatting

        for msg in messages:
            content = msg.get("content", "")
            total_chars += len(content)

        estimated = (total_chars // _CHARS_PER_TOKEN) + (len(messages) * overhead_per_message)
        return estimated

    def needs_compaction(self, messages: List[Dict[str, str]]) -> bool:
        """
        Check if messages exceed the compaction threshold.

        Args:
            messages: List of message dicts.

        Returns:
            True if estimated tokens exceed threshold.
        """
        from config import settings

        threshold = settings.context_summarize_threshold
        estimated = self.estimate_tokens(messages)
        return estimated > threshold

    async def compact(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
    ) -> List[Dict[str, str]]:
        """
        Compact messages to fit within context window.

        Strategy:
          1. Keep system message (first message if role == 'system')
          2. Keep last N messages (recent context)
          3. Summarize middle messages using LLM (or rule-based fallback)
          4. Return compacted message list

        Args:
            messages: Full message history.
            model: Model to use for summarization.

        Returns:
            Compacted list of messages.
        """
        if not messages:
            return messages

        if not self.needs_compaction(messages):
            return messages

        # Separate system message
        system_msg: Optional[Dict[str, str]] = None
        working_messages = list(messages)

        if working_messages and working_messages[0].get("role") == "system":
            system_msg = working_messages[0]
            working_messages = working_messages[1:]

        # Keep last 6 messages as recent context
        keep_recent = 6
        if len(working_messages) <= keep_recent:
            return messages  # Not enough to compact

        recent_messages = working_messages[-keep_recent:]
        older_messages = working_messages[:-keep_recent]

        # Try LLM-based summarization
        summary = await self._llm_summarize(older_messages, model)

        if summary is None:
            # Fallback: rule-based truncation
            summary = self._rule_based_summary(older_messages)

        # Build compacted message list
        result: List[Dict[str, str]] = []
        if system_msg:
            result.append(system_msg)

        result.append({
            "role": "system",
            "content": f"[Context Summary]\n{summary}",
        })
        result.extend(recent_messages)

        logger.info(
            "Context compacted: %d messages -> %d messages (estimated %d -> %d tokens)",
            len(messages),
            len(result),
            self.estimate_tokens(messages),
            self.estimate_tokens(result),
        )

        return result

    async def _llm_summarize(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
    ) -> Optional[str]:
        """
        Summarize messages using LLM.

        Returns None if LLM call fails.
        """
        try:
            from tools.llm_client import call_ollama

            # Build summarization prompt
            conversation_text = "\n".join(
                f"[{msg.get('role', 'unknown')}]: {msg.get('content', '')[:500]}"
                for msg in messages
            )

            summary_messages = [
                {
                    "role": "system",
                    "content": (
                        "You are a conversation summarizer. Summarize the following "
                        "conversation into a concise paragraph capturing key decisions, "
                        "actions taken, and important context. Be brief but preserve "
                        "critical information."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Summarize this conversation:\n\n{conversation_text[:8000]}",
                },
            ]

            from config import settings

            summary_model = model or settings.default_light_model

            result = await call_ollama(
                messages=summary_messages,
                model=summary_model,
                temperature=0.3,
                max_tokens=500,
            )

            if result.get("error"):
                logger.warning("LLM summarization failed: %s", result["error"])
                return None

            content = result.get("content", "").strip()
            if content:
                return content

            return None

        except Exception as e:
            logger.warning("LLM summarization error: %s", e)
            return None

    def _rule_based_summary(self, messages: List[Dict[str, str]]) -> str:
        """
        Rule-based fallback for context compaction.

        Takes the first and last few messages from the older set,
        extracts key content, and produces a brief summary.
        """
        if not messages:
            return "No prior context."

        parts: List[str] = []

        # First message (beginning of conversation)
        first = messages[0]
        first_content = first.get("content", "")[:200]
        parts.append(f"Conversation began with: {first_content}")

        # Count by role
        role_counts: Dict[str, int] = {}
        for msg in messages:
            role = msg.get("role", "unknown")
            role_counts[role] = role_counts.get(role, 0) + 1

        parts.append(
            f"({len(messages)} messages: "
            + ", ".join(f"{count} {role}" for role, count in role_counts.items())
            + ")"
        )

        # Last assistant message summary
        for msg in reversed(messages):
            if msg.get("role") == "assistant":
                content = msg.get("content", "")[:300]
                parts.append(f"Last assistant response covered: {content}")
                break

        return "\n".join(parts)


context_manager = ContextManager()
