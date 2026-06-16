"""Topic Detector — Input classification and routing."""

import re
from typing import Optional


class TopicDetector:
    """Classify user input to determine routing."""

    # Pattern-based classification
    PATTERNS = {
        "command": [
            r"^/(review|explain|fix|refactor|test|document|plan|architect|debug|optimize)\b",
            r"^(run|execute|deploy|build|install|start|stop)\b",
        ],
        "question": [
            r"^(what|how|why|when|where|who|which|can|could|would|should|is|are|do|does)\b",
            r"\?$",
        ],
        "edit": [
            r"^(change|modify|update|replace|rename|move|add|remove|delete)\b",
            r"^(fix|patch|correct)\b",
        ],
        "feedback": [
            r"^(good|great|thanks|perfect|wrong|bad|no|yes|correct|incorrect)\b",
            r"^(i like|i don't|that's wrong|that's right)\b",
        ],
        "clarification": [
            r"^(i mean|actually|sorry|let me|to clarify|what i meant)\b",
            r"^(no,|well,|actually,)\b",
        ],
    }

    def classify(self, message: str) -> str:
        """Classify message type.

        Returns: new_task, follow_up, question, edit, command, feedback, clarification
        """
        message_lower = message.strip().lower()

        # Check command patterns first (slash commands)
        if message.startswith("/"):
            return "command"

        # Check each pattern category
        for category, patterns in self.PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, message_lower):
                    return category

        # Default to new_task for longer messages, follow_up for short
        if len(message.split()) > 10:
            return "new_task"
        return "follow_up"

    def should_reset_context(self, topic_type: str) -> bool:
        """Determine if context should reset."""
        return topic_type in ("new_task", "command")


# Global instance
topic_detector = TopicDetector()
