"""MiLyfe Brain — Slash Command System."""

from __future__ import annotations

import re
from typing import Any, Callable, Dict, Optional, Tuple

import structlog

logger = structlog.get_logger()


# Command registry
SLASH_COMMANDS: Dict[str, Dict[str, Any]] = {}


def register_command(name: str, description: str, handler: Callable):
    """Register a slash command."""
    SLASH_COMMANDS[name] = {"description": description, "handler": handler}


def parse_slash_command(text: str) -> Tuple[Optional[str], str]:
    """Parse a slash command from input. Returns (command, remaining_text)."""
    match = re.match(r"^/(\w+)\s*(.*)", text, re.DOTALL)
    if match:
        return match.group(1), match.group(2).strip()
    return None, text


async def execute_slash_command(command: str, args: str, context: dict = None) -> str:
    """Execute a slash command."""
    if command not in SLASH_COMMANDS:
        available = ", ".join(f"/{c}" for c in SLASH_COMMANDS)
        return f"Unknown command: /{command}\nAvailable: {available}"

    handler = SLASH_COMMANDS[command]["handler"]
    import asyncio
    if asyncio.iscoroutinefunction(handler):
        return await handler(args, context or {})
    return handler(args, context or {})


# ─── Built-in Commands ──────────────────────────────────────────


async def _cmd_review(args: str, ctx: dict) -> str:
    """Review code in a file or selection."""
    from agents.factory import agent_factory
    from models.schemas import AgentRole
    task = f"Review this code critically. Identify bugs, security issues, and improvements:\n\n{args}"
    return await agent_factory.execute_task(role=AgentRole.CRITIC, task=task)


async def _cmd_explain(args: str, ctx: dict) -> str:
    """Explain code or concept."""
    from agents.factory import agent_factory
    from models.schemas import AgentRole
    task = f"Explain this clearly for a developer:\n\n{args}"
    return await agent_factory.execute_task(role=AgentRole.WRITER, task=task)


async def _cmd_fix(args: str, ctx: dict) -> str:
    """Fix a bug or error."""
    from agents.factory import agent_factory
    from models.schemas import AgentRole
    task = f"Debug and fix this issue:\n\n{args}"
    return await agent_factory.execute_task(role=AgentRole.DEBUGGER, task=task)


async def _cmd_test(args: str, ctx: dict) -> str:
    """Generate tests for code."""
    from agents.factory import agent_factory
    from models.schemas import AgentRole
    task = f"Write comprehensive tests for:\n\n{args}"
    return await agent_factory.execute_task(role=AgentRole.CRITIC, task=task)


async def _cmd_refactor(args: str, ctx: dict) -> str:
    """Refactor code."""
    from agents.factory import agent_factory
    from models.schemas import AgentRole
    task = f"Refactor this code for clarity, performance, and maintainability:\n\n{args}"
    return await agent_factory.execute_task(role=AgentRole.CODER, task=task)


async def _cmd_doc(args: str, ctx: dict) -> str:
    """Generate documentation."""
    from agents.factory import agent_factory
    from models.schemas import AgentRole
    task = f"Write clear documentation for:\n\n{args}"
    return await agent_factory.execute_task(role=AgentRole.WRITER, task=task)


async def _cmd_plan(args: str, ctx: dict) -> str:
    """Plan an implementation."""
    from agents.factory import agent_factory
    from models.schemas import AgentRole
    task = f"Create a detailed implementation plan for:\n\n{args}"
    return await agent_factory.execute_task(role=AgentRole.PLANNER, task=task)


# Register built-in commands
register_command("review", "Code review", _cmd_review)
register_command("explain", "Explain code/concept", _cmd_explain)
register_command("fix", "Fix a bug", _cmd_fix)
register_command("test", "Generate tests", _cmd_test)
register_command("refactor", "Refactor code", _cmd_refactor)
register_command("doc", "Generate docs", _cmd_doc)
register_command("plan", "Plan implementation", _cmd_plan)
