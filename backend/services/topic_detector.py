"""MiLyfe Brain — Input Topic Detection / Classification."""

from __future__ import annotations

import re
from typing import Dict, Tuple

from models.schemas import TopicType


def detect_topic(text: str, history_length: int = 0) -> Tuple[TopicType, float]:
    """Classify user input into topic type.

    Returns (topic_type, confidence).
    Fast heuristic handles 80%+ of cases.
    """
    text_lower = text.lower().strip()

    # Commands (slash commands or explicit)
    if text_lower.startswith("/"):
        return TopicType.COMMAND, 0.99

    # Feedback
    feedback_patterns = [
        r"^(good|great|thanks|perfect|nice|awesome|well done)",
        r"(that'?s? (right|correct|good|perfect))",
        r"^(yes|no|nope|yep|exactly)",
    ]
    for pattern in feedback_patterns:
        if re.search(pattern, text_lower):
            return TopicType.FEEDBACK, 0.8

    # Clarification request
    clarification_patterns = [
        r"^(what do you mean|can you explain|i don'?t understand)",
        r"(what|which|how)\s+(exactly|specifically)",
        r"^(clarify|elaborate|expand on)",
    ]
    for pattern in clarification_patterns:
        if re.search(pattern, text_lower):
            return TopicType.CLARIFICATION, 0.85

    # Edit request
    edit_patterns = [
        r"^(change|modify|update|fix|edit|replace|rename)",
        r"(instead|rather|actually,?\s*(make|change|use))",
        r"^(can you (change|modify|update|fix))",
    ]
    for pattern in edit_patterns:
        if re.search(pattern, text_lower):
            return TopicType.EDIT, 0.8

    # Question
    question_patterns = [
        r"^(what|how|why|when|where|who|which|can|could|would|is|are|do|does)\b",
        r"\?$",
    ]
    for pattern in question_patterns:
        if re.search(pattern, text_lower):
            return TopicType.QUESTION, 0.75

    # Follow-up (short messages with context dependency)
    if history_length > 0 and len(text.split()) < 10:
        follow_up_indicators = [
            "also", "and", "additionally", "another",
            "next", "then", "now", "same",
        ]
        if any(w in text_lower.split() for w in follow_up_indicators):
            return TopicType.FOLLOW_UP, 0.7

    # Default: new task
    return TopicType.NEW_TASK, 0.6


def should_reset_context(topic: TopicType) -> bool:
    """Determine if context should reset based on topic type."""
    reset_topics = {TopicType.NEW_TASK}
    return topic in reset_topics
