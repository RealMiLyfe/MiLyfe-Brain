"""Central Tool Registry for MiLyfe Brain.

Manages tool registration, permission enforcement, and lifecycle hooks.
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import Any, Callable, Awaitable, Dict, List, Optional

logger = logging.getLogger(__name__)


class Permission(str, Enum):
    """Permission tiers for tool execution."""

    FREE = "free"          # No approval needed
    NOTIFY = "notify"      # User is notified but execution proceeds
    APPROVE = "approve"    # Requires explicit user approval
    BLOCKED = "blocked"    # Cannot be executed


ToolHandler = Callable[..., Awaitable[str]]
HookFn = Callable[[str, Dict[str, Any]], Awaitable[None]]


class ToolRegistry:
    """Central registry for all available tools.

    Provides registration, lookup, listing, and permission-checked execution
    with support for pre- and post-execution hooks.
    """

    def __init__(self) -> None:
        self._tools: Dict[str, Dict[str, Any]] = {}
        self._pre_hooks: List[HookFn] = []
        self._post_hooks: List[HookFn] = []

    # ─── Registration ─────────────────────────────────────────────────

    def register(
        self,
        name: str,
        func: ToolHandler,
        description: str,
        parameters: Dict[str, Any],
        permission: str = "free",
    ) -> None:
        """Register a tool with the registry.

        Args:
            name: Unique tool identifier.
            func: Async callable that implements the tool.
            description: Human-readable description of what the tool does.
            parameters: Parameter schema dict for the tool.
            permission: Permission level (free, notify, approve, blocked).
        """
        perm = Permission(permission)
        self._tools[name] = {
            "name": name,
            "description": description,
            "parameters": parameters,
            "permission": perm,
            "handler": func,
        }
        logger.debug("Registered tool: %s (permission=%s)", name, perm.value)

    # ─── Lookup ───────────────────────────────────────────────────────

    def get(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a tool definition by name, or None if not found."""
        return self._tools.get(name)

    def list_all(self) -> List[Dict[str, Any]]:
        """Return all registered tools as a list of dicts (without handlers).

        Each dict contains: name, description, parameters, permission.
        """
        result: List[Dict[str, Any]] = []
        for tool in self._tools.values():
            result.append({
                "name": tool["name"],
                "description": tool["description"],
                "parameters": tool["parameters"],
                "permission": tool["permission"].value,
            })
        return result

    # ─── Execution ────────────────────────────────────────────────────

    async def execute(
        self,
        name: str,
        arguments: Dict[str, Any],
        *,
        approved: bool = False,
    ) -> str:
        """Execute a tool by name with the given arguments.

        Args:
            name: Tool name to execute.
            arguments: Keyword arguments to pass to the tool handler.
            approved: Whether the call has been pre-approved (for approve-level tools).

        Returns:
            String result from the tool execution.

        Raises:
            ValueError: If the tool is not found.
            PermissionError: If the tool is blocked or requires unapproved approval.
        """
        tool = self._tools.get(name)
        if tool is None:
            raise ValueError(f"Tool not found: {name}")

        permission: Permission = tool["permission"]

        # Permission enforcement
        if permission == Permission.BLOCKED:
            raise PermissionError(f"Tool '{name}' is blocked and cannot be executed.")
        if permission == Permission.APPROVE and not approved:
            raise PermissionError(
                f"Tool '{name}' requires approval. Set approved=True after user confirmation."
            )

        # Run pre-hooks
        for hook in self._pre_hooks:
            try:
                await hook(name, arguments)
            except Exception as exc:
                logger.warning("Pre-hook failed for tool %s: %s", name, exc)

        # Execute the tool handler
        handler: ToolHandler = tool["handler"]
        try:
            result = await handler(**arguments)
        except Exception as exc:
            logger.error("Tool %s execution failed: %s", name, exc)
            raise

        # Run post-hooks
        for hook in self._post_hooks:
            try:
                await hook(name, {"arguments": arguments, "result": result})
            except Exception as exc:
                logger.warning("Post-hook failed for tool %s: %s", name, exc)

        return result

    # ─── Hooks ────────────────────────────────────────────────────────

    def add_pre_hook(self, hook: HookFn) -> None:
        """Add a pre-execution hook. Called with (tool_name, arguments)."""
        self._pre_hooks.append(hook)

    def add_post_hook(self, hook: HookFn) -> None:
        """Add a post-execution hook. Called with (tool_name, {arguments, result})."""
        self._post_hooks.append(hook)

    # ─── Utilities ────────────────────────────────────────────────────

    def has(self, name: str) -> bool:
        """Check whether a tool is registered."""
        return name in self._tools

    def count(self) -> int:
        """Return the number of registered tools."""
        return len(self._tools)

    def __repr__(self) -> str:
        return f"<ToolRegistry tools={self.count()}>"


# ─── Singleton instance ───────────────────────────────────────────────
tool_registry = ToolRegistry()
