"""
MiLyfe Brain - Code Execution Tools

Sandboxed Python code execution with RestrictedPython.
"""
from __future__ import annotations

import io
import sys
import traceback
from contextlib import redirect_stdout, redirect_stderr
from typing import Any, Dict, TYPE_CHECKING

from models.schemas import PermissionLevel

if TYPE_CHECKING:
    from tools.registry import ToolRegistry

# Safe builtins for restricted execution
SAFE_BUILTINS = {
    "abs": abs,
    "all": all,
    "any": any,
    "bin": bin,
    "bool": bool,
    "bytes": bytes,
    "callable": callable,
    "chr": chr,
    "complex": complex,
    "dict": dict,
    "divmod": divmod,
    "enumerate": enumerate,
    "filter": filter,
    "float": float,
    "format": format,
    "frozenset": frozenset,
    "getattr": getattr,
    "hasattr": hasattr,
    "hash": hash,
    "hex": hex,
    "id": id,
    "int": int,
    "isinstance": isinstance,
    "issubclass": issubclass,
    "iter": iter,
    "len": len,
    "list": list,
    "map": map,
    "max": max,
    "min": min,
    "next": next,
    "oct": oct,
    "ord": ord,
    "pow": pow,
    "print": print,
    "range": range,
    "repr": repr,
    "reversed": reversed,
    "round": round,
    "set": set,
    "slice": slice,
    "sorted": sorted,
    "str": str,
    "sum": sum,
    "tuple": tuple,
    "type": type,
    "zip": zip,
    "None": None,
    "True": True,
    "False": False,
}

# Allowed imports in restricted mode
ALLOWED_IMPORTS = {
    "math",
    "json",
    "re",
    "datetime",
    "collections",
    "itertools",
    "functools",
    "string",
    "textwrap",
    "random",
    "statistics",
    "decimal",
    "fractions",
    "hashlib",
    "base64",
    "urllib.parse",
    "dataclasses",
    "typing",
    "copy",
    "operator",
    "numbers",
}


def _restricted_import(name: str, *args: Any, **kwargs: Any) -> Any:
    """Import function that only allows safe modules."""
    if name not in ALLOWED_IMPORTS:
        raise ImportError(f"Import of '{name}' is not allowed in sandbox")
    return __builtins__["__import__"](name, *args, **kwargs) if isinstance(__builtins__, dict) else __import__(name, *args, **kwargs)


def _execute_restricted(code: str, timeout: int = 30) -> str:
    """Execute code using RestrictedPython sandbox.

    Args:
        code: Python code to execute.
        timeout: Execution timeout in seconds.

    Returns:
        Captured stdout output or error message.
    """
    try:
        from RestrictedPython import compile_restricted, safe_globals
        from RestrictedPython.Eval import default_guarded_getiter
        from RestrictedPython.Guards import (
            guarded_unpack_sequence,
            safer_getattr,
        )

        compiled = compile_restricted(code, "<sandbox>", "exec")

        if compiled.errors:
            return "Compilation errors:\n" + "\n".join(compiled.errors)

        restricted_globals: Dict[str, Any] = safe_globals.copy()
        restricted_globals["__builtins__"]["__import__"] = _restricted_import
        restricted_globals["_getiter_"] = default_guarded_getiter
        restricted_globals["_unpack_sequence_"] = guarded_unpack_sequence
        restricted_globals["_getattr_"] = safer_getattr
        restricted_globals["_write_"] = lambda x: x
        restricted_globals["_inplacevar_"] = lambda op, x, y: op(x, y)

        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()

        with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
            exec(compiled, restricted_globals)  # noqa: S102

        stdout_text = stdout_capture.getvalue()
        stderr_text = stderr_capture.getvalue()

        parts = []
        if stdout_text:
            parts.append(stdout_text.rstrip())
        if stderr_text:
            parts.append(f"STDERR:\n{stderr_text.rstrip()}")
        return "\n".join(parts) if parts else "(no output)"

    except ImportError:
        # RestrictedPython not available, fall back to basic exec
        return _execute_basic(code, timeout)


def _execute_basic(code: str, timeout: int = 30) -> str:
    """Fallback basic exec with limited builtins.

    Args:
        code: Python code to execute.
        timeout: Execution timeout (advisory, not enforced in basic mode).

    Returns:
        Captured stdout output or error message.
    """
    sandbox_globals: Dict[str, Any] = {"__builtins__": SAFE_BUILTINS.copy()}
    sandbox_globals["__builtins__"]["__import__"] = _restricted_import

    stdout_capture = io.StringIO()
    stderr_capture = io.StringIO()

    try:
        compiled = compile(code, "<sandbox>", "exec")
        with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
            exec(compiled, sandbox_globals)  # noqa: S102
    except Exception as e:
        tb = traceback.format_exc()
        return f"Error: {type(e).__name__}: {e}\n\nTraceback:\n{tb}"

    stdout_text = stdout_capture.getvalue()
    stderr_text = stderr_capture.getvalue()

    parts = []
    if stdout_text:
        parts.append(stdout_text.rstrip())
    if stderr_text:
        parts.append(f"STDERR:\n{stderr_text.rstrip()}")
    return "\n".join(parts) if parts else "(no output)"


def code_exec(code: str, timeout: int = 30) -> str:
    """Execute Python code in a sandboxed environment.

    Args:
        code: Python code to execute.
        timeout: Execution timeout in seconds (max 120).

    Returns:
        Captured output (stdout + stderr) or error message.
    """
    if not code.strip():
        return "Error: No code provided"

    timeout = min(max(timeout, 1), 120)

    # Check for obviously dangerous code
    dangerous_patterns = ["os.system", "subprocess", "shutil.rmtree", "__import__('os"]
    code_lower = code.lower()
    for pattern in dangerous_patterns:
        if pattern in code_lower:
            return f"Error: Code contains blocked pattern: '{pattern}'"

    try:
        result = _execute_restricted(code, timeout)
    except Exception as e:
        result = f"Execution error: {type(e).__name__}: {e}"

    # Truncate long output
    if len(result) > 10000:
        result = result[:10000] + "\n\n... (output truncated at 10000 chars)"

    return result


def register_code_tools(registry: ToolRegistry) -> None:
    """Register code execution tools with the tool registry."""
    registry.register(
        name="code_exec",
        handler=code_exec,
        category="code",
        description="Execute Python code in a sandboxed environment with restricted builtins.",
        parameters={
            "code": {"type": "string", "description": "Python code to execute", "required": True},
            "timeout": {"type": "integer", "description": "Timeout in seconds (max 120)", "default": 30},
        },
        permission=PermissionLevel.MODERATE,
        returns="Captured stdout/stderr output or error message",
    )
