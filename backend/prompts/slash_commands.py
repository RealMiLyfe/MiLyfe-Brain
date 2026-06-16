"""Slash Commands — /review, /explain, /fix, etc."""

from typing import Optional


SLASH_COMMANDS = {
    "/review": {
        "description": "Code review — analyze code for issues",
        "prompt_prefix": "Please review the following code for bugs, security issues, performance, and best practices. Provide specific line-level feedback:\n\n",
        "agent_role": "critic",
    },
    "/explain": {
        "description": "Explain code or concept",
        "prompt_prefix": "Please explain the following in detail, breaking down complex parts:\n\n",
        "agent_role": "writer",
    },
    "/fix": {
        "description": "Fix a bug or issue",
        "prompt_prefix": "Please diagnose and fix the following issue. Show the corrected code:\n\n",
        "agent_role": "debugger",
    },
    "/refactor": {
        "description": "Refactor code for better quality",
        "prompt_prefix": "Please refactor the following code to improve readability, performance, and maintainability:\n\n",
        "agent_role": "coder",
    },
    "/test": {
        "description": "Generate tests",
        "prompt_prefix": "Please write comprehensive tests for the following code. Include edge cases:\n\n",
        "agent_role": "critic",
    },
    "/document": {
        "description": "Generate documentation",
        "prompt_prefix": "Please write comprehensive documentation for the following:\n\n",
        "agent_role": "writer",
    },
    "/plan": {
        "description": "Create a plan",
        "prompt_prefix": "Please create a detailed, actionable plan for the following goal:\n\n",
        "agent_role": "planner",
    },
    "/architect": {
        "description": "Design system architecture",
        "prompt_prefix": "Please design the system architecture for the following requirement:\n\n",
        "agent_role": "designer",
    },
    "/debug": {
        "description": "Debug an error",
        "prompt_prefix": "Please analyze this error and provide a solution:\n\n",
        "agent_role": "debugger",
    },
    "/optimize": {
        "description": "Optimize performance",
        "prompt_prefix": "Please optimize the following for better performance:\n\n",
        "agent_role": "coder",
    },
}


def parse_slash_command(message: str) -> Optional[dict]:
    """Parse a slash command from user input.

    Returns dict with command info or None if not a slash command.
    """
    message = message.strip()
    if not message.startswith("/"):
        return None

    parts = message.split(" ", 1)
    command = parts[0].lower()
    content = parts[1] if len(parts) > 1 else ""

    if command in SLASH_COMMANDS:
        cmd_info = SLASH_COMMANDS[command]
        return {
            "command": command,
            "content": content,
            "prompt": cmd_info["prompt_prefix"] + content,
            "agent_role": cmd_info["agent_role"],
            "description": cmd_info["description"],
        }

    return None


def list_slash_commands() -> list[dict]:
    """List all available slash commands."""
    return [
        {"command": cmd, "description": info["description"], "agent_role": info["agent_role"]}
        for cmd, info in SLASH_COMMANDS.items()
    ]
