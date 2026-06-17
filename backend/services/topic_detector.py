"""
MiLyfe Brain - Topic Detector

Keyword/regex heuristic-based topic classification for user messages.
Detects the primary topic type of a text input.
"""
from __future__ import annotations

import logging
import re
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)


def detect_topic(text: str) -> str:
    """
    Detect the primary topic of a text using keyword/regex heuristics.

    Args:
        text: Input text to classify.

    Returns:
        TopicType value string (e.g., 'coding', 'research', 'general').
    """
    if not text or not text.strip():
        return "general"

    text_lower = text.lower().strip()

    # Score each topic
    scores: Dict[str, float] = {}
    for topic, patterns in _TOPIC_PATTERNS.items():
        score = 0.0
        for pattern, weight in patterns:
            if re.search(pattern, text_lower):
                score += weight
        scores[topic] = score

    # Return highest scoring topic (if above threshold)
    if scores:
        best_topic = max(scores, key=scores.get)  # type: ignore[arg-type]
        if scores[best_topic] > 0.0:
            return best_topic

    return "general"


# ============================================================
# Topic Pattern Definitions
# Each pattern is (regex, weight) — higher weight = stronger signal.
# ============================================================

_TOPIC_PATTERNS: Dict[str, List[Tuple[str, float]]] = {
    "coding": [
        (r"\b(code|coding|program|function|class|method|variable)\b", 2.0),
        (r"\b(python|javascript|typescript|rust|java|go|c\+\+|ruby)\b", 3.0),
        (r"\b(api|endpoint|database|sql|query|schema)\b", 2.0),
        (r"\b(bug|fix|error|exception|traceback|stack\s?trace)\b", 2.5),
        (r"\b(implement|refactor|optimize|compile|build|deploy)\b", 2.0),
        (r"\b(import|export|module|package|library|framework)\b", 1.5),
        (r"\b(git|commit|branch|merge|pull\s?request|pr)\b", 1.5),
        (r"\b(test|unit\s?test|integration|coverage|assert)\b", 1.5),
        (r"```", 3.0),  # Code fences
        (r"\b(def|const|let|var|return|if|else|for|while)\b", 2.0),
    ],
    "debugging": [
        (r"\b(debug|debugging|debugger)\b", 3.0),
        (r"\b(error|exception|crash|fail|broken|not\s?working)\b", 2.5),
        (r"\b(traceback|stack\s?trace|segfault|panic)\b", 3.0),
        (r"\b(fix|solve|resolve|troubleshoot|diagnose)\b", 2.0),
        (r"\b(log|logs|logging|stderr|stdout)\b", 1.5),
        (r"\b(why|what\s?went\s?wrong|root\s?cause)\b", 1.5),
        (r"error:", 2.0),
        (r"traceback \(most recent call last\)", 4.0),
    ],
    "research": [
        (r"\b(research|study|investigate|explore|survey)\b", 2.5),
        (r"\b(find|search|look\s?up|discover|compare)\b", 1.5),
        (r"\b(paper|article|documentation|source|reference)\b", 2.0),
        (r"\b(pros?\s?(?:and|&)\s?cons?|trade-?off|alternative)\b", 2.0),
        (r"\b(benchmark|performance|comparison)\b", 1.5),
        (r"\b(best\s?practice|recommendation|state-of-the-art)\b", 2.0),
        (r"\b(what\s?is|how\s?does|explain|overview)\b", 1.0),
    ],
    "writing": [
        (r"\b(write|writing|draft|compose|author)\b", 2.5),
        (r"\b(essay|article|blog|post|document|report)\b", 2.5),
        (r"\b(edit|rewrite|proofread|grammar|tone)\b", 2.0),
        (r"\b(summary|summarize|abstract|outline)\b", 2.0),
        (r"\b(email|letter|message|response|reply)\b", 1.5),
        (r"\b(markdown|format|heading|paragraph)\b", 1.5),
        (r"\b(readme|changelog|documentation)\b", 1.5),
    ],
    "planning": [
        (r"\b(plan|planning|roadmap|timeline|milestone)\b", 3.0),
        (r"\b(architecture|design|structure|organize)\b", 2.0),
        (r"\b(project|sprint|epic|story|task|ticket)\b", 2.0),
        (r"\b(schedule|deadline|estimate|priority)\b", 2.0),
        (r"\b(step|steps|workflow|process|pipeline)\b", 1.5),
        (r"\b(break\s?down|decompose|divide|split)\b", 2.0),
        (r"\b(goal|objective|requirement|spec)\b", 1.5),
    ],
    "brainstorming": [
        (r"\b(brainstorm|idea|ideas|creative|innovate)\b", 3.0),
        (r"\b(suggest|suggestion|propose|proposal)\b", 2.0),
        (r"\b(what\s?if|could\s?we|how\s?about|maybe)\b", 1.5),
        (r"\b(explore|possibilities|options|approach)\b", 1.5),
        (r"\b(think|thoughts|opinion|perspective)\b", 1.0),
        (r"\b(generate|come\s?up\s?with|list|braindump)\b", 2.0),
    ],
    "analysis": [
        (r"\b(analy[sz]e|analysis|examine|inspect|audit)\b", 3.0),
        (r"\b(metric|metrics|data|statistics|numbers)\b", 2.0),
        (r"\b(pattern|trend|insight|observation)\b", 2.0),
        (r"\b(performance|bottleneck|profile|profiling)\b", 2.0),
        (r"\b(security|vulnerability|risk|assessment)\b", 2.0),
        (r"\b(review|evaluate|assess|measure)\b", 1.5),
        (r"\b(report|dashboard|visualization)\b", 1.5),
    ],
}
