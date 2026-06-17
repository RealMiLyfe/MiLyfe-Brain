"""MiLyfe Brain — Hook Execution Engine."""

from __future__ import annotations

from typing import Any, List

import structlog

from models.schemas import ToolCall, ToolResult

logger = structlog.get_logger()


class HookRegistry:
    """Manages pre/post tool hooks."""

    def __init__(self):
        self._pre_hooks: List[Any] = []
        self._post_hooks: List[Any] = []

    def register_pre_hook(self, hook):
        """Register a pre-tool hook."""
        self._pre_hooks.append(hook)

    def register_post_hook(self, hook):
        """Register a post-tool hook."""
        self._post_hooks.append(hook)

    async def run_pre_hooks(self, tool_call: ToolCall, agent: Any) -> ToolCall:
        """Run all pre-hooks. Can modify or block the call."""
        for hook in self._pre_hooks:
            try:
                tool_call = await hook.process(tool_call, agent)
            except Exception as e:
                logger.warning("pre_hook_error", hook=type(hook).__name__, error=str(e))
        return tool_call

    async def run_post_hooks(self, result: ToolResult, agent: Any) -> ToolResult:
        """Run all post-hooks. Can transform output."""
        for hook in self._post_hooks:
            try:
                result = await hook.process(result, agent)
            except Exception as e:
                logger.warning("post_hook_error", hook=type(hook).__name__, error=str(e))
        return result


# Singleton
hook_registry = HookRegistry()
