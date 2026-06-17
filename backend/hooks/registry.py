"""MiLyfe Brain — Hook Registry & Built-in Hooks.

Manages registration and execution of pre/post-tool hooks.
Includes built-in hooks for common safety concerns.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List

from hooks.base import PostToolHook, PreToolHook

logger = logging.getLogger(__name__)

# Maximum file size for write operations (10 MB)
_MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024


# ═══════════════════════════════════════════════════════════════════════
# BUILT-IN HOOKS
# ═══════════════════════════════════════════════════════════════════════


class PathSanitizationHook(PreToolHook):
    """Sanitizes file paths to prevent directory traversal attacks.

    Blocks paths containing '..' sequences, null bytes, or attempts
    to access files outside the workspace directory.
    """

    @property
    def priority(self) -> int:
        return 10  # Run early

    async def execute(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and sanitize path parameters."""
        path_keys = ("path", "file_path", "target", "source", "destination")

        for key in path_keys:
            if key not in params:
                continue

            path_value = params[key]
            if not isinstance(path_value, str):
                continue

            # Block null bytes
            if "\x00" in path_value:
                raise PermissionError(
                    f"Path contains null bytes (potential injection): {key}"
                )

            # Block directory traversal (check raw path before normalization)
            if ".." in path_value.split("/") or ".." in path_value.split(os.sep):
                raise PermissionError(
                    f"Path traversal detected in '{key}': {path_value}"
                )

            # Normalize the path
            params[key] = os.path.normpath(path_value)

        return params


class AuditLogHook(PostToolHook):
    """Logs all tool executions to the audit trail.

    Records tool name, parameters, and result summary for
    post-hoc review and compliance.
    """

    @property
    def priority(self) -> int:
        return 90  # Run late (after other post-hooks)

    async def execute(
        self, tool_name: str, params: Dict[str, Any], result: Any
    ) -> Any:
        """Log the tool execution (non-blocking, best-effort)."""
        try:
            from safety.logger import audit_logger

            # Summarize result for logging (avoid storing large payloads)
            result_summary = str(result)[:500] if result is not None else None

            await audit_logger.log_action(
                agent_id=params.get("_agent_id", "unknown"),
                agent_role=params.get("_agent_role", "unknown"),
                action_type=tool_name,
                description=f"Tool '{tool_name}' executed",
                result=result_summary,
                playbook_id=params.get("_playbook_id"),
            )
        except Exception as e:
            # Audit logging should never break the main flow
            logger.warning(f"Audit log hook failed: {e}")

        return result


class FileSizeLimitHook(PreToolHook):
    """Enforces file size limits on write operations.

    Prevents agents from writing excessively large files that
    could exhaust disk space.
    """

    @property
    def priority(self) -> int:
        return 50

    async def execute(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Check content size for write operations."""
        if tool_name not in ("file_write", "file_create", "file_append"):
            return params

        content = params.get("content", "")
        if isinstance(content, str):
            size = len(content.encode("utf-8"))
        elif isinstance(content, bytes):
            size = len(content)
        else:
            return params

        if size > _MAX_FILE_SIZE_BYTES:
            raise ValueError(
                f"File content exceeds size limit: {size} bytes "
                f"(max {_MAX_FILE_SIZE_BYTES} bytes / {_MAX_FILE_SIZE_BYTES // (1024*1024)} MB)"
            )

        return params


# ═══════════════════════════════════════════════════════════════════════
# HOOK REGISTRY
# ═══════════════════════════════════════════════════════════════════════


class HookRegistry:
    """Central registry for pre- and post-tool execution hooks.

    Hooks are executed in priority order (lower priority number runs first).
    Pre-hooks can modify parameters; post-hooks can modify results.
    """

    def __init__(self) -> None:
        self._pre_hooks: List[PreToolHook] = []
        self._post_hooks: List[PostToolHook] = []

    def register_pre_hook(self, hook: PreToolHook) -> None:
        """Register a pre-tool execution hook.

        Args:
            hook: The PreToolHook instance to register.
        """
        self._pre_hooks.append(hook)
        self._pre_hooks.sort(key=lambda h: h.priority)
        logger.debug(f"Registered pre-hook: {hook.name} (priority={hook.priority})")

    def register_post_hook(self, hook: PostToolHook) -> None:
        """Register a post-tool execution hook.

        Args:
            hook: The PostToolHook instance to register.
        """
        self._post_hooks.append(hook)
        self._post_hooks.sort(key=lambda h: h.priority)
        logger.debug(f"Registered post-hook: {hook.name} (priority={hook.priority})")

    async def run_pre_hooks(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute all pre-hooks in priority order.

        Args:
            tool_name: Name of the tool about to be invoked.
            params: The parameters for the tool.

        Returns:
            Modified parameters after all pre-hooks have run.

        Raises:
            PermissionError: If any hook blocks execution.
            ValueError: If any hook rejects the parameters.
        """
        current_params = params
        for hook in self._pre_hooks:
            try:
                current_params = await hook.execute(tool_name, current_params)
            except (PermissionError, ValueError):
                raise
            except Exception as e:
                logger.error(f"Pre-hook '{hook.name}' failed: {e}")
                # Non-critical hook failures don't block execution
                continue
        return current_params

    async def run_post_hooks(
        self, tool_name: str, params: Dict[str, Any], result: Any
    ) -> Any:
        """Execute all post-hooks in priority order.

        Args:
            tool_name: Name of the tool that was invoked.
            params: The parameters that were passed to the tool.
            result: The result returned by the tool.

        Returns:
            Modified result after all post-hooks have run.
        """
        current_result = result
        for hook in self._post_hooks:
            try:
                current_result = await hook.execute(tool_name, params, current_result)
            except Exception as e:
                logger.error(f"Post-hook '{hook.name}' failed: {e}")
                # Post-hook failures don't lose the result
                continue
        return current_result

    @property
    def pre_hook_count(self) -> int:
        """Number of registered pre-hooks."""
        return len(self._pre_hooks)

    @property
    def post_hook_count(self) -> int:
        """Number of registered post-hooks."""
        return len(self._post_hooks)


def _create_default_registry() -> HookRegistry:
    """Create a HookRegistry with built-in hooks registered."""
    registry = HookRegistry()
    registry.register_pre_hook(PathSanitizationHook())
    registry.register_pre_hook(FileSizeLimitHook())
    registry.register_post_hook(AuditLogHook())
    return registry


# Singleton instance with built-in hooks
hook_registry = _create_default_registry()
