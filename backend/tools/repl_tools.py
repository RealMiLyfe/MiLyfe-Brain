"""MiLyfe Brain — Persistent REPL Session Tools."""

from __future__ import annotations

from typing import Any, Dict

from models.schemas import PermissionLevel

# Persistent REPL sessions (variables survive between calls)
_repl_sessions: Dict[str, Dict[str, Any]] = {}
_default_session = "default"


async def repl_execute(code: str, session_id: str = "default") -> str:
    """Execute Python code in a persistent session.

    Variables survive between calls (unlike code_exec which is stateless).
    """
    import io
    import sys
    import traceback

    # Get or create session namespace
    if session_id not in _repl_sessions:
        _repl_sessions[session_id] = {"__builtins__": __builtins__}

    namespace = _repl_sessions[session_id]

    # Capture output
    output_buffer = io.StringIO()
    old_stdout = sys.stdout
    sys.stdout = output_buffer

    try:
        # Try eval first (for expressions)
        try:
            result = eval(code, namespace)
            output = output_buffer.getvalue()
            if result is not None:
                output += repr(result)
            return output if output else repr(result) if result is not None else "(no output)"
        except SyntaxError:
            pass

        # Fall back to exec (for statements)
        exec(code, namespace)
        output = output_buffer.getvalue()
        return output if output else "(executed, no output)"

    except Exception as e:
        return f"Error: {type(e).__name__}: {e}\n{traceback.format_exc()}"
    finally:
        sys.stdout = old_stdout


async def repl_inspect(variable: str, session_id: str = "default") -> str:
    """Inspect a variable in a REPL session."""
    if session_id not in _repl_sessions:
        return f"Session '{session_id}' not found"

    namespace = _repl_sessions[session_id]
    if variable not in namespace:
        return f"Variable '{variable}' not defined"

    val = namespace[variable]
    return f"Type: {type(val).__name__}\nValue: {repr(val)[:2000]}"


async def repl_variables(session_id: str = "default") -> str:
    """List all user-defined variables in a REPL session."""
    if session_id not in _repl_sessions:
        return f"Session '{session_id}' not found"

    namespace = _repl_sessions[session_id]
    user_vars = {
        k: type(v).__name__
        for k, v in namespace.items()
        if not k.startswith("_") and k != "__builtins__"
    }

    if not user_vars:
        return "(no variables defined)"

    lines = [f"  {name}: {type_name}" for name, type_name in sorted(user_vars.items())]
    return f"Variables ({len(user_vars)}):\n" + "\n".join(lines)


def register_repl_tools(registry):
    """Register REPL tools."""
    registry.register(
        name="repl_execute",
        handler=repl_execute,
        category="REPL",
        description="Execute Python in persistent session (vars survive)",
        parameters={"code": "str", "session_id": "str"},
        permission=PermissionLevel.NOTIFY,
    )
    registry.register(
        name="repl_inspect",
        handler=repl_inspect,
        category="REPL",
        description="Inspect a variable in REPL session",
        parameters={"variable": "str", "session_id": "str"},
        permission=PermissionLevel.FREE,
    )
    registry.register(
        name="repl_variables",
        handler=repl_variables,
        category="REPL",
        description="List all REPL session variables",
        parameters={"session_id": "str"},
        permission=PermissionLevel.FREE,
    )
