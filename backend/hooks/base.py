"""MiLyfe Brain — Pre/Post Tool Hook ABCs and Built-in Hooks."""

from __future__ import annotations

import abc
import os
from typing import Any

import structlog

from models.schemas import ToolCall, ToolResult

logger = structlog.get_logger()


class PreToolHook(abc.ABC):
    """Abstract base for pre-tool hooks. Can modify params or block."""

    @abc.abstractmethod
    async def process(self, tool_call: ToolCall, agent: Any) -> ToolCall:
        ...


class PostToolHook(abc.ABC):
    """Abstract base for post-tool hooks. Can transform output."""

    @abc.abstractmethod
    async def process(self, result: ToolResult, agent: Any) -> ToolResult:
        ...


# ─── Built-in Pre-Hooks ────────────────────────────────────────


class PathSanitizationHook(PreToolHook):
    """Sanitize file paths to prevent directory traversal."""

    async def process(self, tool_call: ToolCall, agent: Any) -> ToolCall:
        if "path" in tool_call.arguments:
            path = tool_call.arguments["path"]
            # Remove .. traversal attempts
            sanitized = os.path.normpath(path).lstrip("/").lstrip("\\")
            sanitized = sanitized.replace("..", "")
            tool_call.arguments["path"] = sanitized
        return tool_call


class FileSizeLimitHook(PreToolHook):
    """Limit file write content size."""

    MAX_SIZE = 5 * 1024 * 1024  # 5MB

    async def process(self, tool_call: ToolCall, agent: Any) -> ToolCall:
        if tool_call.tool_name == "file_write":
            content = tool_call.arguments.get("content", "")
            if len(content) > self.MAX_SIZE:
                raise ValueError(f"File content too large ({len(content)} bytes, max {self.MAX_SIZE})")
        return tool_call


# ─── Built-in Post-Hooks ───────────────────────────────────────


class OutputTruncationHook(PostToolHook):
    """Truncate very long outputs to prevent context overflow."""

    MAX_OUTPUT = 10000

    async def process(self, result: ToolResult, agent: Any) -> ToolResult:
        if result.output and len(result.output) > self.MAX_OUTPUT:
            result.output = result.output[:self.MAX_OUTPUT] + "\n...[truncated]..."
        return result


class AutoFormatHook(PostToolHook):
    """Auto-format output for readability."""

    async def process(self, result: ToolResult, agent: Any) -> ToolResult:
        # Strip excessive whitespace
        if result.output:
            lines = result.output.split("\n")
            # Remove trailing blank lines
            while lines and not lines[-1].strip():
                lines.pop()
            result.output = "\n".join(lines)
        return result


# Register built-in hooks
def register_builtin_hooks():
    """Register all built-in hooks with the registry."""
    from hooks.registry import hook_registry

    hook_registry.register_pre_hook(PathSanitizationHook())
    hook_registry.register_pre_hook(FileSizeLimitHook())
    hook_registry.register_post_hook(OutputTruncationHook())
    hook_registry.register_post_hook(AutoFormatHook())


# Auto-register on import
register_builtin_hooks()
