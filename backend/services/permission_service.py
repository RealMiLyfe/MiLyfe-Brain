"""
MiLyfe Brain - Permission Service

Checks whether a given tool invocation is permitted for a specific agent role.
Enforces safety boundaries and approval requirements.
"""
from __future__ import annotations

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)

# Permission matrix: tool categories and their allowed roles / risk levels
_TOOL_PERMISSIONS: Dict[str, Dict[str, Any]] = {
    # File operations
    "file_read": {"allowed_roles": None, "risk": "safe"},  # None = all roles
    "file_write": {"allowed_roles": ["coder", "executor", "orchestrator"], "risk": "moderate"},
    "file_delete": {"allowed_roles": ["executor", "orchestrator"], "risk": "destructive"},
    # Shell
    "shell_exec": {"allowed_roles": ["executor", "coder", "orchestrator"], "risk": "destructive"},
    # Browser
    "browser_navigate": {"allowed_roles": ["browser", "researcher"], "risk": "moderate"},
    "browser_click": {"allowed_roles": ["browser"], "risk": "moderate"},
    "browser_input": {"allowed_roles": ["browser"], "risk": "moderate"},
    # GUI
    "gui_click": {"allowed_roles": ["gui"], "risk": "destructive"},
    "gui_type": {"allowed_roles": ["gui"], "risk": "destructive"},
    "gui_screenshot": {"allowed_roles": ["gui", "browser"], "risk": "safe"},
    # Code execution
    "code_execute": {"allowed_roles": ["coder", "executor"], "risk": "destructive"},
    "repl_execute": {"allowed_roles": ["coder", "executor"], "risk": "moderate"},
    # Search
    "web_search": {"allowed_roles": None, "risk": "safe"},
    "file_search": {"allowed_roles": None, "risk": "safe"},
    # Memory
    "memory_store": {"allowed_roles": None, "risk": "safe"},
    "memory_recall": {"allowed_roles": None, "risk": "safe"},
    # Batch operations
    "batch_execute": {"allowed_roles": ["executor", "orchestrator"], "risk": "moderate"},
}

# Dangerous argument patterns
_DANGEROUS_PATTERNS = [
    "rm -rf /",
    "rm -rf ~",
    "mkfs",
    ":(){:|:&};:",
    "dd if=/dev/zero",
    "chmod -R 777 /",
    "> /dev/sda",
]


def check_permission(
    tool_name: str,
    arguments: Dict[str, Any],
    agent_role: str,
) -> bool:
    """
    Check if an agent has permission to execute a tool with given arguments.

    Args:
        tool_name: Name of the tool being invoked.
        arguments: Arguments passed to the tool.
        agent_role: Role of the agent requesting the action.

    Returns:
        True if permitted, False if denied.
    """
    from config import settings

    # Look up tool permissions
    tool_config = _TOOL_PERMISSIONS.get(tool_name)

    if tool_config is None:
        # Unknown tool — default to allow but log
        logger.debug("Unknown tool '%s' — defaulting to allow", tool_name)
        return True

    # Check role permission
    allowed_roles = tool_config.get("allowed_roles")
    if allowed_roles is not None:
        if agent_role not in allowed_roles:
            logger.warning(
                "Permission denied: role '%s' cannot use tool '%s' (allowed: %s)",
                agent_role, tool_name, allowed_roles,
            )
            return False

    # Check risk level against settings
    risk = tool_config.get("risk", "safe")
    if risk == "destructive" and settings.require_approval_destructive:
        # For destructive ops, check if command is safe
        command = arguments.get("command", "") or arguments.get("cmd", "")
        if _is_dangerous_command(command):
            logger.warning(
                "Permission denied: dangerous command detected in '%s': %s",
                tool_name, command[:100],
            )
            return False

    # Check for dangerous argument patterns
    for key, value in arguments.items():
        if isinstance(value, str) and _is_dangerous_command(value):
            logger.warning(
                "Permission denied: dangerous pattern in argument '%s' for tool '%s'",
                key, tool_name,
            )
            return False

    return True


def _is_dangerous_command(command: str) -> bool:
    """Check if a command matches known dangerous patterns."""
    if not command:
        return False

    command_lower = command.lower().strip()
    for pattern in _DANGEROUS_PATTERNS:
        if pattern in command_lower:
            return True

    return False


def get_risk_level(tool_name: str) -> str:
    """
    Get the risk level for a tool.

    Args:
        tool_name: Tool name.

    Returns:
        Risk level string: 'safe', 'moderate', 'destructive', or 'critical'.
    """
    tool_config = _TOOL_PERMISSIONS.get(tool_name, {})
    return tool_config.get("risk", "safe")
