"""Output Styles — concise, verbose, architect, pair_programmer, etc."""


OUTPUT_STYLES = {
    "default": {
        "name": "Default",
        "instruction": "Respond naturally with clear explanations. Use code blocks for code.",
    },
    "concise": {
        "name": "Concise",
        "instruction": "Be extremely brief. Use bullet points. No filler words. Code only when needed.",
    },
    "verbose": {
        "name": "Verbose",
        "instruction": "Provide detailed explanations. Include context, alternatives, and trade-offs. Explain your reasoning step by step.",
    },
    "architect": {
        "name": "Architect",
        "instruction": "Think at the system level. Focus on design patterns, scalability, maintainability. Use diagrams (ASCII/mermaid). Consider edge cases and failure modes.",
    },
    "pair_programmer": {
        "name": "Pair Programmer",
        "instruction": "Think out loud. Explain your thought process. Ask clarifying questions. Suggest alternatives. Be collaborative and conversational.",
    },
    "diff_only": {
        "name": "Diff Only",
        "instruction": "Respond ONLY with code changes in diff format. No explanations unless explicitly asked. Use unified diff format.",
    },
    "junior_friendly": {
        "name": "Junior Friendly",
        "instruction": "Explain everything as if teaching a junior developer. Define technical terms. Provide examples. Link concepts to fundamentals.",
    },
    "senior": {
        "name": "Senior",
        "instruction": "Assume expert knowledge. Skip basics. Focus on nuances, edge cases, and advanced patterns. Be direct and technical.",
    },
}

# Current active style
_current_style: str = "default"


def get_style_instruction(style: str = None) -> str:
    """Get the instruction for a style."""
    style = style or _current_style
    style_info = OUTPUT_STYLES.get(style, OUTPUT_STYLES["default"])
    return f"\n## Output Style: {style_info['name']}\n{style_info['instruction']}"


def set_style(style: str) -> bool:
    """Set the active output style."""
    global _current_style
    if style in OUTPUT_STYLES:
        _current_style = style
        return True
    return False


def get_current_style() -> str:
    """Get current active style name."""
    return _current_style


def list_styles() -> list[dict]:
    """List all available output styles."""
    return [{"id": k, "name": v["name"], "instruction": v["instruction"]} for k, v in OUTPUT_STYLES.items()]
