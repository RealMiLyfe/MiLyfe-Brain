"""MiLyfe Brain — Permission System.

Tiered permission levels control which actions agents can perform
without user intervention. Maps tool names to permission tiers.
"""

from __future__ import annotations

from enum import Enum
from typing import Dict


class PermissionLevel(str, Enum):
    """Permission tiers from least to most restrictive."""

    free = "free"
    notify = "notify"
    approve = "approve"
    blocked = "blocked"


# Default permission mapping for built-in tools
_DEFAULT_TOOL_PERMISSIONS: Dict[str, PermissionLevel] = {
    "file_read": PermissionLevel.free,
    "file_write": PermissionLevel.notify,
    "file_delete": PermissionLevel.approve,
    "shell_exec": PermissionLevel.notify,
    "code_exec": PermissionLevel.notify,
    "browse_web": PermissionLevel.approve,
    "gui_action": PermissionLevel.approve,
    "glob_search": PermissionLevel.free,
    "grep_search": PermissionLevel.free,
}


class PermissionService:
    """Manages permission levels for tool invocations.

    Provides a centralized check for whether a given tool or action
    requires user approval, notification, or can proceed freely.
    """

    def __init__(self, tool_permissions: Dict[str, PermissionLevel] | None = None) -> None:
        self._tool_permissions: Dict[str, PermissionLevel] = dict(_DEFAULT_TOOL_PERMISSIONS)
        if tool_permissions:
            self._tool_permissions.update(tool_permissions)

    def check_permission(self, action_type: str) -> PermissionLevel:
        """Check the permission level for a given action type.

        Args:
            action_type: The type of action being performed (e.g., 'file_write').

        Returns:
            The PermissionLevel for the action. Defaults to 'notify' for unknown actions.
        """
        return self._tool_permissions.get(action_type, PermissionLevel.notify)

    def get_level_for_tool(self, tool_name: str) -> PermissionLevel:
        """Get the permission level required for a specific tool.

        Args:
            tool_name: Name of the tool to check.

        Returns:
            The PermissionLevel for the tool. Defaults to 'notify' for unknown tools.
        """
        return self._tool_permissions.get(tool_name, PermissionLevel.notify)

    def is_allowed(self, tool_name: str) -> bool:
        """Check whether a tool is allowed to execute (not blocked).

        Args:
            tool_name: Name of the tool to check.

        Returns:
            True if the tool is not blocked, False otherwise.
        """
        level = self.get_level_for_tool(tool_name)
        return level != PermissionLevel.blocked

    def set_permission(self, tool_name: str, level: PermissionLevel) -> None:
        """Override the permission level for a tool.

        Args:
            tool_name: Name of the tool to configure.
            level: The new PermissionLevel to assign.
        """
        self._tool_permissions[tool_name] = level

    def get_all_permissions(self) -> Dict[str, PermissionLevel]:
        """Return a copy of the current permission mapping."""
        return dict(self._tool_permissions)


# Singleton instance
permission_service = PermissionService()
