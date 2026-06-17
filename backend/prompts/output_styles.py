"""MiLyfe Brain — Output Style System.

Defines output formatting styles that can be appended to system prompts
to control how agents format their responses.
"""

from __future__ import annotations

from typing import Dict

# Output style definitions
OUTPUT_STYLES: Dict[str, str] = {
    "default": (
        "Respond in a clear, professional manner. Use markdown formatting where appropriate. "
        "Include code blocks with language identifiers. Balance brevity with completeness. "
        "Provide context and explanations alongside code."
    ),
    "concise": (
        "Be extremely concise. Use bullet points and short sentences. "
        "Skip unnecessary explanations — get straight to the answer. "
        "Only include code that directly solves the problem. No filler text."
    ),
    "verbose": (
        "Provide thorough, detailed explanations. Cover all edge cases and alternatives. "
        "Include complete code with comments. Explain your reasoning step by step. "
        "Mention potential pitfalls, trade-offs, and best practices."
    ),
    "architect": (
        "Respond as a senior software architect. Focus on system design, trade-offs, "
        "and scalability considerations. Use diagrams (mermaid/ASCII) where helpful. "
        "Reference design patterns, architectural principles, and industry best practices. "
        "Consider non-functional requirements."
    ),
    "pair_programmer": (
        "Respond as an engaged pair programming partner. Think out loud about the problem. "
        "Ask clarifying questions when something is ambiguous. Suggest alternatives and "
        "discuss trade-offs collaboratively. Write code incrementally, explaining choices."
    ),
    "diff_only": (
        "Respond ONLY with code diffs in unified diff format. No explanations, "
        "no commentary — just the changes needed. Use ```diff code blocks. "
        "Include file paths in the diff headers. Show minimal context lines."
    ),
    "junior_friendly": (
        "Explain everything as if teaching a junior developer. Define technical terms "
        "on first use. Break complex concepts into small steps. Include 'why' explanations "
        "for every decision. Provide links to relevant documentation. Use analogies."
    ),
    "code_only": (
        "Respond ONLY with code. No explanations, no comments unless critical, "
        "no markdown text outside code blocks. Include complete, runnable code. "
        "Use appropriate language-specific code blocks."
    ),
}


def get_style(name: str) -> str:
    """Get an output style by name.

    Args:
        name: The style name (e.g., 'concise', 'verbose').

    Returns:
        The style instruction string. Falls back to 'default' if
        the requested style is not found.
    """
    return OUTPUT_STYLES.get(name, OUTPUT_STYLES["default"])


def list_styles() -> Dict[str, str]:
    """Return all available styles with abbreviated descriptions.

    Returns:
        Dict mapping style names to their first sentence.
    """
    return {
        name: style.split(".")[0] + "."
        for name, style in OUTPUT_STYLES.items()
    }
