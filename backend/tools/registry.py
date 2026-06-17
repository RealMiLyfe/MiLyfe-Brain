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
        agent_id: Optional[str] = None,
        agent_role: Optional[str] = None,
    ) -> str:
        """Execute a tool by name with the given arguments.

        Args:
            name: Tool name to execute.
            arguments: Keyword arguments to pass to the tool handler.
            approved: Whether the call has been pre-approved (for approve-level tools).
            agent_id: ID of the requesting agent (for approval tracking).
            agent_role: Role of the requesting agent.

        Returns:
            String result from the tool execution.

        Raises:
            ValueError: If the tool is not found.
            PermissionError: If the tool is blocked or approval denied.
        """
        tool = self._tools.get(name)
        if tool is None:
            raise ValueError(f"Tool not found: {name}")

        permission: Permission = tool["permission"]

        # Permission enforcement
        if permission == Permission.BLOCKED:
            raise PermissionError(f"Tool '{name}' is blocked and cannot be executed.")

        if permission == Permission.APPROVE and not approved:
            # Request human approval via the approval service
            try:
                from safety.approvals import approval_service, ApprovalStatus
                from agents.message_bus import get_message_bus, Topic

                # Notify frontend via message bus
                bus = get_message_bus()
                desc = f"Agent wants to execute '{name}' with args: {arguments}"
                
                # Publish approval request event for WebSocket clients
                approval_request = await approval_service.request_approval(
                    action_type=name,
                    description=desc,
                    details=str(arguments)[:500],
                    agent_id=agent_id,
                    agent_role=agent_role,
                    timeout=300.0,
                )

                # Emit event so frontend shows the approval dialog
                await bus.publish(
                    topic=Topic.STATUS_UPDATE,
                    payload={
                        "event_type": "approval_required",
                        "id": approval_request.id,
                        "action_type": name,
                        "description": desc,
                        "agent_id": agent_id,
                        "agent_role": agent_role,
                        "risk_level": "high",
                    },
                    sender_id=agent_id or "tool_registry",
                )

                if approval_request.status == ApprovalStatus.approved:
                    logger.info("Tool '%s' approved by user", name)
                elif approval_request.status == ApprovalStatus.denied:
                    raise PermissionError(f"Tool '{name}' execution denied by user.")
                else:
                    raise PermissionError(f"Tool '{name}' approval expired (timeout).")
            except (ImportError, Exception) as e:
                if "PermissionError" in type(e).__name__ or isinstance(e, PermissionError):
                    raise
                # If approval system isn't available, fall back to blocking
                raise PermissionError(
                    f"Tool '{name}' requires approval but approval system unavailable: {e}"
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
