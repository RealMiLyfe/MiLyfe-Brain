"""Hook Execution Engine — Manages pre/post hook pipeline."""

from typing import Any, Optional

import structlog

from hooks.base import PostToolHook, PreToolHook

logger = structlog.get_logger()


class HookRegistry:
    """Registry and executor for tool hooks."""

    def __init__(self):
        self._pre_hooks: list[PreToolHook] = []
        self._post_hooks: list[PostToolHook] = []

    def register_pre_hook(self, hook: PreToolHook) -> None:
        """Register a pre-tool hook."""
        self._pre_hooks.append(hook)

    def register_post_hook(self, hook: PostToolHook) -> None:
        """Register a post-tool hook."""
        self._post_hooks.append(hook)

    async def run_pre_hooks(self, tool_name: str, params: dict, context: dict) -> Optional[dict]:
        """Run all pre-hooks in order.

        Returns modified params or None if blocked.
        """
        current_params = params.copy()

        for hook in self._pre_hooks:
            try:
                result = await hook.before(tool_name, current_params, context)
                if result is None:
                    logger.info("Tool blocked by pre-hook", tool=tool_name, hook=type(hook).__name__)
                    return None
                current_params = result
            except Exception as e:
                logger.error("Pre-hook error", hook=type(hook).__name__, error=str(e))

        return current_params

    async def run_post_hooks(self, tool_name: str, params: dict, result: Any, context: dict) -> Any:
        """Run all post-hooks in order."""
        current_result = result

        for hook in self._post_hooks:
            try:
                current_result = await hook.after(tool_name, params, current_result, context)
            except Exception as e:
                logger.error("Post-hook error", hook=type(hook).__name__, error=str(e))

        return current_result


# Global instance with built-in hooks
hook_registry = HookRegistry()

# Register built-in hooks
from hooks.base import PathSanitizationHook, FileSizeLimitHook, AuditLogHook, AutoFormatHook

hook_registry.register_pre_hook(PathSanitizationHook())
hook_registry.register_post_hook(FileSizeLimitHook())
hook_registry.register_post_hook(AuditLogHook())
hook_registry.register_post_hook(AutoFormatHook())
