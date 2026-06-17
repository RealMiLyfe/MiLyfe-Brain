"""MiLyfe Brain — Slash Command System.

Maps slash commands to system prompt injections that modify agent behavior.
Supports parsing user input to extract commands.
"""

from __future__ import annotations

from typing import Dict, Optional, Tuple

# Slash command definitions: command -> system prompt injection
SLASH_COMMANDS: Dict[str, str] = {
    "/review": (
        "You are performing a thorough code review. Analyze the code for: "
        "bugs, security vulnerabilities, performance issues, code style violations, "
        "and maintainability concerns. Provide specific line-by-line feedback with "
        "severity levels (critical, warning, suggestion). Suggest concrete fixes."
    ),
    "/explain": (
        "You are explaining code to a developer. Break down the logic step by step. "
        "Explain the purpose of each function, the data flow, design patterns used, "
        "and any non-obvious behavior. Use clear language and provide examples where helpful."
    ),
    "/fix": (
        "You are diagnosing and fixing a bug or issue. Identify the root cause, "
        "explain why the problem occurs, and provide a corrected implementation. "
        "Show the diff between the original and fixed code. Consider edge cases."
    ),
    "/test": (
        "You are writing comprehensive tests. Generate unit tests covering: "
        "happy paths, edge cases, error conditions, and boundary values. "
        "Use appropriate testing frameworks. Aim for high code coverage and "
        "meaningful assertions. Include test descriptions explaining intent."
    ),
    "/doc": (
        "You are writing documentation. Generate clear, comprehensive documentation "
        "including: module/function docstrings, usage examples, parameter descriptions, "
        "return value specifications, and any important notes or caveats. "
        "Follow the project's documentation style."
    ),
    "/refactor": (
        "You are refactoring code for improved quality. Focus on: "
        "reducing complexity, improving readability, eliminating duplication, "
        "applying SOLID principles, and improving naming. Preserve all existing "
        "behavior (no functional changes). Explain each refactoring decision."
    ),
    "/security": (
        "You are performing a security audit. Check for: "
        "injection vulnerabilities (SQL, XSS, command), authentication/authorization flaws, "
        "sensitive data exposure, insecure configurations, dependency vulnerabilities, "
        "and OWASP Top 10 issues. Rate each finding by severity and exploitability."
    ),
    "/optimize": (
        "You are optimizing code for performance. Identify bottlenecks, "
        "suggest algorithmic improvements, reduce memory allocations, "
        "minimize I/O operations, and leverage caching where appropriate. "
        "Provide benchmarking suggestions and explain the expected improvement."
    ),
}


def parse_slash_command(input_text: str) -> Tuple[Optional[str], str]:
    """Parse user input to extract a slash command and remaining text.

    If the input starts with a recognized slash command, returns the
    command and the remaining input. Otherwise returns None and the
    full input unchanged.

    Args:
        input_text: The full user input string.

    Returns:
        Tuple of (command_or_none, remaining_input).
        - If a command is found: ("/command", "rest of input")
        - If no command: (None, "original input")

    Examples:
        >>> parse_slash_command("/review Check this function")
        ("/review", "Check this function")
        >>> parse_slash_command("Just a normal message")
        (None, "Just a normal message")
    """
    if not input_text or not input_text.startswith("/"):
        return None, input_text

    stripped = input_text.strip()
    parts = stripped.split(maxsplit=1)
    command = parts[0].lower()
    remaining = parts[1] if len(parts) > 1 else ""

    if command in SLASH_COMMANDS:
        return command, remaining

    return None, input_text


def get_command_prompt(command: str) -> Optional[str]:
    """Get the system prompt injection for a slash command.

    Args:
        command: The slash command (e.g., '/review').

    Returns:
        The system prompt string, or None if command is not recognized.
    """
    return SLASH_COMMANDS.get(command)


def list_commands() -> Dict[str, str]:
    """Return all available slash commands with their first-line descriptions.

    Returns:
        Dict mapping command names to brief descriptions.
    """
    return {
        cmd: prompt.split(".")[0] + "."
        for cmd, prompt in SLASH_COMMANDS.items()
    }
