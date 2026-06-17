"""MiLyfe Brain — Output Style Definitions."""

from __future__ import annotations

from typing import Dict

from models.schemas import OutputStyle

# Style instruction templates appended to system prompts
STYLE_INSTRUCTIONS: Dict[OutputStyle, str] = {
    OutputStyle.DEFAULT: "",
    OutputStyle.CONCISE: (
        "Be extremely concise. Short sentences. No filler. "
        "Bullet points preferred. Skip preamble."
    ),
    OutputStyle.VERBOSE: (
        "Be thorough and detailed. Explain your reasoning step by step. "
        "Include examples. Cover edge cases. Don't assume prior knowledge."
    ),
    OutputStyle.ARCHITECT: (
        "Think like a senior software architect. Focus on design patterns, "
        "trade-offs, scalability, and maintainability. Use diagrams (ASCII) "
        "when helpful. Consider the big picture."
    ),
    OutputStyle.PAIR_PROGRAMMER: (
        "Act as a pair programmer. Think out loud. Suggest alternatives. "
        "Ask clarifying questions. Share your reasoning. Be collaborative."
    ),
    OutputStyle.DIFF_ONLY: (
        "Show ONLY code changes in unified diff format. "
        "No explanation unless explicitly asked. "
        "Format: ```diff\\n-old\\n+new\\n```"
    ),
    OutputStyle.JUNIOR_FRIENDLY: (
        "Explain as if teaching a junior developer. Be patient. "
        "Define jargon. Provide context for WHY, not just HOW. "
        "Include links to relevant docs when possible."
    ),
    OutputStyle.TUTORIAL: (
        "Write as a step-by-step tutorial. Number each step. "
        "Include code samples with comments. Explain what each part does. "
        "Build complexity gradually."
    ),
}


def get_style_instruction(style: OutputStyle) -> str:
    """Get the instruction string for a style."""
    return STYLE_INSTRUCTIONS.get(style, "")


def apply_style_to_prompt(system_prompt: str, style: OutputStyle) -> str:
    """Append style instructions to a system prompt."""
    instruction = get_style_instruction(style)
    if instruction:
        return f"{system_prompt}\n\n[Output Style: {style.value}]\n{instruction}"
    return system_prompt
