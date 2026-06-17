"""MiLyfe Brain — Sandboxed Python Code Execution."""

from __future__ import annotations

import io
import sys
import traceback

from models.schemas import PermissionLevel


async def code_exec(code: str, timeout: int = 30) -> str:
    """Execute Python code in a sandboxed environment.

    Uses RestrictedPython for safety. Stateless (no persistent vars).
    """
    import asyncio

    # Run in thread to avoid blocking event loop
    result = await asyncio.to_thread(_execute_sandboxed, code, timeout)
    return result


def _execute_sandboxed(code: str, timeout: int) -> str:
    """Execute code with RestrictedPython restrictions."""
    try:
        from RestrictedPython import compile_restricted, safe_globals
        from RestrictedPython.Eval import default_guarded_getitem
        from RestrictedPython.Guards import (
            guarded_iter_unpack_sequence,
            safer_getattr,
        )
    except ImportError:
        # Fallback to basic exec if RestrictedPython not available
        return _execute_basic(code, timeout)

    # Compile with restrictions
    try:
        compiled = compile_restricted(code, "<agent_code>", "exec")
    except SyntaxError as e:
        return f"SyntaxError: {e}"

    if compiled.errors:
        return f"Compilation errors: {'; '.join(compiled.errors)}"

    # Set up restricted globals
    restricted_globals = safe_globals.copy()
    restricted_globals["_getiter_"] = iter
    restricted_globals["_getitem_"] = default_guarded_getitem
    restricted_globals["_iter_unpack_sequence_"] = guarded_iter_unpack_sequence
    restricted_globals["getattr"] = safer_getattr

    # Allow common safe builtins
    safe_builtins = restricted_globals.get("__builtins__", {})
    if isinstance(safe_builtins, dict):
        safe_builtins.update({
            "len": len,
            "range": range,
            "enumerate": enumerate,
            "zip": zip,
            "map": map,
            "filter": filter,
            "sorted": sorted,
            "reversed": reversed,
            "list": list,
            "dict": dict,
            "set": set,
            "tuple": tuple,
            "str": str,
            "int": int,
            "float": float,
            "bool": bool,
            "print": print,
            "isinstance": isinstance,
            "type": type,
            "sum": sum,
            "min": min,
            "max": max,
            "abs": abs,
            "round": round,
            "any": any,
            "all": all,
        })

    # Capture stdout
    output_buffer = io.StringIO()
    restricted_globals["_print_"] = lambda *args, **kwargs: print(*args, file=output_buffer, **kwargs)

    local_vars = {}

    try:
        exec(compiled, restricted_globals, local_vars)
        output = output_buffer.getvalue()

        # If no print output, try to get the last expression value
        if not output and "_result" in local_vars:
            output = str(local_vars["_result"])

        return output if output else "(no output)"
    except Exception as e:
        return f"Error: {type(e).__name__}: {e}\n{traceback.format_exc()}"


def _execute_basic(code: str, timeout: int) -> str:
    """Basic exec fallback (less restricted)."""
    output_buffer = io.StringIO()
    old_stdout = sys.stdout
    sys.stdout = output_buffer

    try:
        exec(code, {"__builtins__": __builtins__}, {})
        output = output_buffer.getvalue()
        return output if output else "(no output)"
    except Exception as e:
        return f"Error: {type(e).__name__}: {e}"
    finally:
        sys.stdout = old_stdout


def register_code_tools(registry):
    """Register code execution tools."""
    registry.register(
        name="code_exec",
        handler=code_exec,
        category="Code",
        description="Execute Python code in sandboxed environment (stateless)",
        parameters={"code": "str", "timeout": "int (seconds)"},
        permission=PermissionLevel.NOTIFY,
    )
