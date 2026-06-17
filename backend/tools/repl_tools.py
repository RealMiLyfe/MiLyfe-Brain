"""
MiLyfe Brain - REPL Tools

Persistent Python REPL sessions with namespace management.
"""
from __future__ import annotations

import io
import traceback
from contextlib import redirect_stdout, redirect_stderr
from datetime import datetime
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from models.schemas import PermissionLevel

if TYPE_CHECKING:
    from tools.registry import ToolRegistry

# Persistent REPL sessions: session_id -> {namespace, history, created_at}
_repl_sessions: Dict[str, Dict[str, Any]] = {}


def _get_session(session_id: str) -> Dict[str, Any]:
    """Get or create a REPL session."""
    if session_id not in _repl_sessions:
        _repl_sessions[session_id] = {
            "namespace": {"__builtins__": __builtins__},
            "history": [],
            "created_at": datetime.utcnow().isoformat(),
        }
    return _repl_sessions[session_id]


def repl_execute(code: str, session_id: str = "default") -> str:
    """Execute code in a persistent REPL session.

    Args:
        code: Python code to execute.
        session_id: Session identifier for namespace isolation.

    Returns:
        Execution output (stdout + last expression value) or error.
    """
    if not code.strip():
        return "Error: No code provided"

    session = _get_session(session_id)
    namespace = session["namespace"]

    stdout_capture = io.StringIO()
    stderr_capture = io.StringIO()

    # Record in history
    session["history"].append({
        "code": code,
        "timestamp": datetime.utcnow().isoformat(),
    })

    try:
        # Try to compile as expression first (to capture return value)
        try:
            compiled = compile(code, f"<repl:{session_id}>", "eval")
            with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                result = eval(compiled, namespace)  # noqa: S307
            stdout_text = stdout_capture.getvalue()
            if stdout_text:
                output = stdout_text.rstrip()
                if result is not None:
                    output += f"\n=> {repr(result)}"
            else:
                output = repr(result) if result is not None else "(no output)"
            return output
        except SyntaxError:
            pass

        # Compile as statements
        compiled = compile(code, f"<repl:{session_id}>", "exec")
        with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
            exec(compiled, namespace)  # noqa: S102

        stdout_text = stdout_capture.getvalue()
        stderr_text = stderr_capture.getvalue()

        parts = []
        if stdout_text:
            parts.append(stdout_text.rstrip())
        if stderr_text:
            parts.append(f"STDERR:\n{stderr_text.rstrip()}")
        return "\n".join(parts) if parts else "(no output)"

    except Exception as e:
        tb = traceback.format_exc()
        return f"Error: {type(e).__name__}: {e}\n\n{tb}"


def repl_inspect(variable: str, session_id: str = "default") -> str:
    """Inspect a variable in a REPL session.

    Args:
        variable: Variable name to inspect.
        session_id: Session identifier.

    Returns:
        Variable type, value, and attributes.
    """
    session = _get_session(session_id)
    namespace = session["namespace"]

    if variable not in namespace:
        available = [k for k in namespace.keys() if not k.startswith("_")]
        return f"Variable '{variable}' not found.\nAvailable: {', '.join(sorted(available)[:20])}"

    value = namespace[variable]
    info_parts = [
        f"Name: {variable}",
        f"Type: {type(value).__name__}",
        f"Value: {repr(value)[:500]}",
    ]

    # Add length for sequences
    if hasattr(value, "__len__"):
        try:
            info_parts.append(f"Length: {len(value)}")
        except TypeError:
            pass

    # Add callable info
    if callable(value):
        import inspect
        try:
            sig = inspect.signature(value)
            info_parts.append(f"Signature: {variable}{sig}")
        except (ValueError, TypeError):
            info_parts.append("Callable: yes")

    # List attributes (non-private)
    attrs = [a for a in dir(value) if not a.startswith("_")]
    if attrs:
        info_parts.append(f"Attributes: {', '.join(attrs[:20])}")
        if len(attrs) > 20:
            info_parts.append(f"  ... and {len(attrs) - 20} more")

    return "\n".join(info_parts)


def repl_variables(session_id: str = "default") -> str:
    """List all user-defined variables in a REPL session.

    Args:
        session_id: Session identifier.

    Returns:
        Formatted list of variables with types and short values.
    """
    session = _get_session(session_id)
    namespace = session["namespace"]

    # Filter out builtins and private vars
    user_vars = {
        k: v for k, v in namespace.items()
        if not k.startswith("_") and k != "__builtins__"
    }

    if not user_vars:
        return f"Session '{session_id}': No user-defined variables"

    lines = [f"Session '{session_id}' variables ({len(user_vars)}):"]
    for name, value in sorted(user_vars.items()):
        type_name = type(value).__name__
        value_repr = repr(value)[:80]
        lines.append(f"  {name}: {type_name} = {value_repr}")

    lines.append(f"\nHistory: {len(session['history'])} executions")
    lines.append(f"Created: {session['created_at']}")
    return "\n".join(lines)


def register_repl_tools(registry: ToolRegistry) -> None:
    """Register REPL tools with the tool registry."""
    registry.register(
        name="repl_execute",
        handler=repl_execute,
        category="repl",
        description="Execute Python code in a persistent REPL session with shared namespace.",
        parameters={
            "code": {"type": "string", "description": "Python code to execute", "required": True},
            "session_id": {"type": "string", "description": "Session ID for namespace isolation", "default": "default"},
        },
        permission=PermissionLevel.MODERATE,
        returns="Execution output or error",
    )
    registry.register(
        name="repl_inspect",
        handler=repl_inspect,
        category="repl",
        description="Inspect a variable in a REPL session (type, value, attributes).",
        parameters={
            "variable": {"type": "string", "description": "Variable name to inspect", "required": True},
            "session_id": {"type": "string", "description": "Session ID", "default": "default"},
        },
        permission=PermissionLevel.SAFE,
        returns="Variable info: type, value, attributes",
    )
    registry.register(
        name="repl_variables",
        handler=repl_variables,
        category="repl",
        description="List all user-defined variables in a REPL session.",
        parameters={
            "session_id": {"type": "string", "description": "Session ID", "default": "default"},
        },
        permission=PermissionLevel.SAFE,
        returns="Formatted variable listing",
    )
