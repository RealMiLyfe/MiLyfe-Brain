"""Persistent REPL tools for MiLyfe Brain.

Provides a persistent Python REPL with session-based namespaces.
"""

from __future__ import annotations

import io
import logging
import traceback
from contextlib import redirect_stdout, redirect_stderr
from typing import Any, Dict

logger = logging.getLogger(__name__)


class PythonREPL:
    """Persistent Python REPL with session-based namespaces.

    Each session maintains its own namespace so variables persist
    across multiple execute() calls within the same session.
    """

    def __init__(self) -> None:
        self._sessions: Dict[str, Dict[str, Any]] = {}

    def _get_namespace(self, session_id: str) -> Dict[str, Any]:
        """Get or create a namespace for the session."""
        if session_id not in self._sessions:
            self._sessions[session_id] = {"__builtins__": __builtins__}
        return self._sessions[session_id]

    def execute(self, code: str, session_id: str = "default") -> str:
        """Execute code in the session namespace.

        Args:
            code: Python code to execute.
            session_id: Session identifier for namespace isolation.

        Returns:
            Captured stdout/stderr output or error.
        """
        namespace = self._get_namespace(session_id)
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()

        try:
            compiled = compile(code, f"<repl:{session_id}>", "exec")
        except SyntaxError as exc:
            return f"[SyntaxError] {exc}"

        try:
            with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                exec(compiled, namespace)  # noqa: S102
        except Exception as exc:
            tb = traceback.format_exc()
            return f"[Error]\n{tb}"

        stdout = stdout_capture.getvalue()
        stderr = stderr_capture.getvalue()

        parts: list[str] = []
        if stdout:
            parts.append(stdout)
        if stderr:
            parts.append(f"[STDERR]\n{stderr}")

        return "\n".join(parts) if parts else "(no output)"

    def inspect(self, variable: str, session_id: str = "default") -> str:
        """Inspect a variable in the session.

        Args:
            variable: Variable name to inspect.
            session_id: Session identifier.

        Returns:
            Detailed representation of the variable.
        """
        namespace = self._get_namespace(session_id)

        if variable not in namespace:
            return f"Variable '{variable}' not found in session '{session_id}'."

        value = namespace[variable]
        lines = [
            f"Variable: {variable}",
            f"Type: {type(value).__name__}",
            f"Value: {repr(value)}",
        ]

        # Add extra info for collections
        if isinstance(value, (list, tuple, set, frozenset, dict)):
            lines.append(f"Length: {len(value)}")

        if hasattr(value, "__doc__") and value.__doc__:
            lines.append(f"Docstring: {value.__doc__[:200]}")

        return "\n".join(lines)

    def list_variables(self, session_id: str = "default") -> str:
        """List all user-defined variables in the session.

        Args:
            session_id: Session identifier.

        Returns:
            Formatted list of variable names, types, and short values.
        """
        namespace = self._get_namespace(session_id)

        # Filter out builtins and dunder names
        user_vars = {
            k: v for k, v in namespace.items()
            if not k.startswith("__") and k != "__builtins__"
        }

        if not user_vars:
            return f"No variables in session '{session_id}'."

        lines = [f"Variables in session '{session_id}':"]
        lines.append("─" * 40)
        for name, value in sorted(user_vars.items()):
            val_repr = repr(value)
            if len(val_repr) > 60:
                val_repr = val_repr[:57] + "..."
            lines.append(f"  {name}: {type(value).__name__} = {val_repr}")

        return "\n".join(lines)

    def reset(self, session_id: str = "default") -> None:
        """Reset a session, clearing all variables."""
        if session_id in self._sessions:
            del self._sessions[session_id]


# ─── Singleton REPL instance ─────────────────────────────────────────
_repl = PythonREPL()


async def repl_execute(code: str, session_id: str = "default") -> str:
    """Execute code in a persistent REPL session.

    Args:
        code: Python code to execute.
        session_id: Session identifier (default: "default").

    Returns:
        Execution output.
    """
    logger.info("repl_execute: session=%s code_len=%d", session_id, len(code))
    return _repl.execute(code, session_id)


async def repl_inspect(variable: str, session_id: str = "default") -> str:
    """Inspect a variable in the REPL session.

    Args:
        variable: Variable name to inspect.
        session_id: Session identifier (default: "default").

    Returns:
        Detailed variable information.
    """
    logger.info("repl_inspect: session=%s variable=%s", session_id, variable)
    return _repl.inspect(variable, session_id)


async def repl_variables(session_id: str = "default") -> str:
    """List all variables in the REPL session.

    Args:
        session_id: Session identifier (default: "default").

    Returns:
        Formatted list of all session variables.
    """
    logger.info("repl_variables: session=%s", session_id)
    return _repl.list_variables(session_id)
