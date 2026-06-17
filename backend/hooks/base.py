"""MiLyfe Brain — Hook Base Classes.

Abstract base classes for pre- and post-tool execution hooks.
Hooks can inspect and modify tool parameters and results.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict


class PreToolHook(ABC):
    """Abstract base class for pre-tool execution hooks.

    Pre-hooks run before a tool is invoked and can modify
    the parameters passed to the tool. They can also raise
    exceptions to prevent execution.
    """

    @property
    def name(self) -> str:
        """Human-readable name of this hook."""
        return self.__class__.__name__

    @property
    def priority(self) -> int:
        """Execution priority (lower runs first). Default: 100."""
        return 100

    @abstractmethod
    async def execute(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the pre-hook logic.

        Args:
            tool_name: Name of the tool about to be invoked.
            params: The parameters that will be passed to the tool.

        Returns:
            Modified (or unmodified) parameters dict. The returned
            dict will be passed to the next hook or to the tool itself.

        Raises:
            PermissionError: If the hook decides to block execution.
            ValueError: If parameters are invalid.
        """
        ...


class PostToolHook(ABC):
    """Abstract base class for post-tool execution hooks.

    Post-hooks run after a tool completes and can inspect or
    modify the result before it's returned to the caller.
    """

    @property
    def name(self) -> str:
        """Human-readable name of this hook."""
        return self.__class__.__name__

    @property
    def priority(self) -> int:
        """Execution priority (lower runs first). Default: 100."""
        return 100

    @abstractmethod
    async def execute(
        self, tool_name: str, params: Dict[str, Any], result: Any
    ) -> Any:
        """Execute the post-hook logic.

        Args:
            tool_name: Name of the tool that was invoked.
            params: The parameters that were passed to the tool.
            result: The result returned by the tool.

        Returns:
            Modified (or unmodified) result. The returned value
            will be passed to the next hook or returned to the caller.
        """
        ...
