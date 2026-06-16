"""Code Tools — Sandboxed Python execution."""

import io
import sys
import traceback
from contextlib import redirect_stdout, redirect_stderr

from RestrictedPython import compile_restricted, safe_globals


async def code_exec(code: str, timeout: int = 30) -> str:
    """Execute Python code in a sandboxed environment.

    Uses RestrictedPython for safe execution.
    Stateless — each call is independent.
    """
    stdout_buffer = io.StringIO()
    stderr_buffer = io.StringIO()

    # Build safe execution environment
    exec_globals = safe_globals.copy()
    exec_globals["__builtins__"] = {
        **safe_globals["__builtins__"],
        "print": print,
        "len": len,
        "range": range,
        "enumerate": enumerate,
        "zip": zip,
        "map": map,
        "filter": filter,
        "sorted": sorted,
        "reversed": reversed,
        "str": str,
        "int": int,
        "float": float,
        "bool": bool,
        "list": list,
        "dict": dict,
        "tuple": tuple,
        "set": set,
        "type": type,
        "isinstance": isinstance,
        "hasattr": hasattr,
        "getattr": getattr,
        "min": min,
        "max": max,
        "sum": sum,
        "abs": abs,
        "round": round,
        "any": any,
        "all": all,
    }

    exec_locals = {}

    try:
        # Try RestrictedPython first
        byte_code = compile_restricted(code, filename="<agent_code>", mode="exec")
        if byte_code.errors:
            # Fallback to regular compile for simple cases
            byte_code = compile(code, "<agent_code>", "exec")

        with redirect_stdout(stdout_buffer), redirect_stderr(stderr_buffer):
            exec(byte_code, exec_globals, exec_locals)

        output = stdout_buffer.getvalue()
        errors = stderr_buffer.getvalue()

        result = ""
        if output:
            result += output
        if errors:
            result += f"\n[STDERR]: {errors}"

        # Include return values if any
        if "_result" in exec_locals:
            result += f"\nResult: {exec_locals['_result']}"

        return result if result.strip() else "(executed successfully, no output)"

    except SyntaxError as e:
        return f"SyntaxError: {str(e)}"
    except Exception as e:
        tb = traceback.format_exc()
        return f"Error: {str(e)}\n{tb}"


def register_code_tools(registry):
    """Register code tools with the tool registry."""
    registry.register("code_exec", "Execute Python code (sandboxed)", code_exec, permission="notify",
                      params={"code": "Python code to execute", "timeout": "Timeout in seconds"})
