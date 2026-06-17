"""Pre/Post Tool Hook Abstract Base Classes."""

from abc import ABC, abstractmethod
from typing import Any, Optional


class PreToolHook(ABC):
    """Hook that runs before tool execution.

    Can modify parameters or block execution.
    """

    @abstractmethod
    async def before(self, tool_name: str, params: dict, context: dict) -> Optional[dict]:
        """Run before tool execution.

        Args:
            tool_name: Name of the tool being called
            params: Tool parameters
            context: Execution context (agent_id, role, etc.)

        Returns:
            Modified params dict, or None to block execution.
        """
        ...


class PostToolHook(ABC):
    """Hook that runs after tool execution.

    Can transform output or add metadata.
    """

    @abstractmethod
    async def after(self, tool_name: str, params: dict, result: Any, context: dict) -> Any:
        """Run after tool execution.

        Args:
            tool_name: Name of the tool that was called
            params: Original tool parameters
            result: Tool execution result
            context: Execution context

        Returns:
            Transformed result.
        """
        ...


# Built-in hooks

class PathSanitizationHook(PreToolHook):
    """Sanitize file paths to prevent directory traversal."""

    async def before(self, tool_name: str, params: dict, context: dict) -> Optional[dict]:
        if "path" in params:
            path = params["path"]
            # Remove dangerous patterns
            path = path.replace("..", "").replace("~", "")
            params["path"] = path
        return params


class FileSizeLimitHook(PostToolHook):
    """Truncate oversized file read results."""

    MAX_SIZE = 100000  # 100KB

    async def after(self, tool_name: str, params: dict, result: Any, context: dict) -> Any:
        if tool_name == "file_read" and isinstance(result, str) and len(result) > self.MAX_SIZE:
            return result[:self.MAX_SIZE] + f"\n...[truncated at {self.MAX_SIZE} chars]"
        return result


class AuditLogHook(PostToolHook):
    """Log all tool executions."""

    async def after(self, tool_name: str, params: dict, result: Any, context: dict) -> Any:
        # Logging is handled by the registry, this is additional structured logging
        return result


class AutoFormatHook(PostToolHook):
    """Auto-format code output."""

    async def after(self, tool_name: str, params: dict, result: Any, context: dict) -> Any:
        # For now, pass through
        return result
