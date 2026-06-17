"""REPL Tools — Persistent Python sessions."""

import io
import sys
import traceback
from contextlib import redirect_stdout, redirect_stderr

# Persistent REPL sessions (per session ID)
_sessions: dict[str, dict] = {}


async def repl_execute(code: str, session_id: str = "default") -> str:
    """Execute code in a persistent REPL session.

    Variables persist between calls within the same session.
    """
    if session_id not in _sessions:
        _sessions[session_id] = {"globals": {"__builtins__": __builtins__}, "locals": {}}

    session = _sessions[session_id]
    stdout_buf = io.StringIO()
    stderr_buf = io.StringIO()

    try:
        with redirect_stdout(stdout_buf), redirect_stderr(stderr_buf):
            exec(code, session["globals"], session["locals"])

        output = stdout_buf.getvalue()
        errors = stderr_buf.getvalue()

        result = ""
        if output:
            result += output
        if errors:
            result += f"\n[STDERR]: {errors}"

        return result if result.strip() else "(executed, no output)"

    except Exception as e:
        tb = traceback.format_exc()
        return f"Error: {str(e)}\n{tb}"


async def repl_inspect(variable: str, session_id: str = "default") -> str:
    """Inspect a variable in the REPL session."""
    if session_id not in _sessions:
        return f"Session '{session_id}' not found"

    session = _sessions[session_id]
    all_vars = {**session["globals"], **session["locals"]}

    if variable in all_vars:
        val = all_vars[variable]
        return f"{variable} = {repr(val)}\nType: {type(val).__name__}"
    elif variable in session["locals"]:
        val = session["locals"][variable]
        return f"{variable} = {repr(val)}\nType: {type(val).__name__}"
    else:
        return f"Variable '{variable}' not found in session"


async def repl_variables(session_id: str = "default") -> str:
    """List all variables in the REPL session."""
    if session_id not in _sessions:
        return f"Session '{session_id}' not found"

    session = _sessions[session_id]
    user_vars = {
        k: type(v).__name__
        for k, v in session["locals"].items()
        if not k.startswith("_")
    }

    if not user_vars:
        return "(no user variables)"

    return "\n".join(f"{k}: {v}" for k, v in user_vars.items())


def register_repl_tools(registry):
    """Register REPL tools with the tool registry."""
    registry.register("repl_execute", "Execute in persistent REPL", repl_execute, permission="notify",
                      params={"code": "Python code", "session_id": "Session identifier"})
    registry.register("repl_inspect", "Inspect REPL variable", repl_inspect, permission="free",
                      params={"variable": "Variable name", "session_id": "Session identifier"})
    registry.register("repl_variables", "List REPL variables", repl_variables, permission="free",
                      params={"session_id": "Session identifier"})
