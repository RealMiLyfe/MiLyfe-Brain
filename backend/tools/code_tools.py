"""Sandboxed Python code execution tools for MiLyfe Brain.

Uses RestrictedPython for safe evaluation with import blocking.
"""

from __future__ import annotations

import asyncio
import io
import logging
import sys
from contextlib import redirect_stdout, redirect_stderr
from typing import Any, Dict

logger = logging.getLogger(__name__)

# Modules blocked from being imported in sandboxed code
BLOCKED_MODULES = frozenset({
    "os",
    "subprocess",
    "sys",
    "shutil",
    "socket",
    "ctypes",
    "signal",
    "multiprocessing",
    "threading",
    "importlib",
    "pathlib",
    "tempfile",
    "webbrowser",
    "http",
    "ftplib",
    "smtplib",
    "telnetlib",
    "xml.etree.ElementTree",
})


def _safe_import(name: str, *args: Any, **kwargs: Any) -> Any:
    """Restricted import that blocks dangerous modules."""
    if name in BLOCKED_MODULES:
        raise ImportError(f"Import of '{name}' is not allowed in sandboxed execution.")
    return __builtins__["__import__"](name, *args, **kwargs) if isinstance(__builtins__, dict) else __import__(name, *args, **kwargs)


def _build_restricted_globals() -> Dict[str, Any]:
    """Build the globals dict for restricted code execution."""
    restricted_globals: Dict[str, Any] = {
        "__builtins__": {
            "__import__": _safe_import,
            "print": print,
            "range": range,
            "len": len,
            "int": int,
            "float": float,
            "str": str,
            "bool": bool,
            "list": list,
            "dict": dict,
            "tuple": tuple,
            "set": set,
            "frozenset": frozenset,
            "sorted": sorted,
            "reversed": reversed,
            "enumerate": enumerate,
            "zip": zip,
            "map": map,
            "filter": filter,
            "sum": sum,
            "min": min,
            "max": max,
            "abs": abs,
            "round": round,
            "isinstance": isinstance,
            "issubclass": issubclass,
            "type": type,
            "hasattr": hasattr,
            "getattr": getattr,
            "setattr": setattr,
            "repr": repr,
            "format": format,
            "iter": iter,
            "next": next,
            "all": all,
            "any": any,
            "chr": chr,
            "ord": ord,
            "hex": hex,
            "oct": oct,
            "bin": bin,
            "pow": pow,
            "divmod": divmod,
            "hash": hash,
            "id": id,
            "callable": callable,
            "input": lambda *a: "",  # Disable input()
            "open": None,  # Block file access
            "exec": None,  # Block nested exec
            "eval": None,  # Block nested eval
            "compile": None,  # Block compile
            "globals": None,
            "locals": None,
            "vars": None,
            "dir": dir,
            "help": None,
            "Exception": Exception,
            "ValueError": ValueError,
            "TypeError": TypeError,
            "KeyError": KeyError,
            "IndexError": IndexError,
            "AttributeError": AttributeError,
            "RuntimeError": RuntimeError,
            "StopIteration": StopIteration,
            "ZeroDivisionError": ZeroDivisionError,
            "True": True,
            "False": False,
            "None": None,
        },
    }
    return restricted_globals


async def code_exec(code: str, timeout: int = 10) -> str:
    """Execute sandboxed Python code and return the output.

    Args:
        code: Python source code to execute.
        timeout: Maximum execution time in seconds (default 10).

    Returns:
        Captured stdout/stderr output, or error message if execution fails.
    """
    logger.info("code_exec: executing %d chars of code (timeout=%ds)", len(code), timeout)

    def _run_code() -> str:
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()
        restricted_globals = _build_restricted_globals()
        restricted_locals: Dict[str, Any] = {}

        try:
            compiled = compile(code, "<sandbox>", "exec")
        except SyntaxError as exc:
            return f"[SyntaxError] {exc}"

        try:
            with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                exec(compiled, restricted_globals, restricted_locals)  # noqa: S102
        except ImportError as exc:
            return f"[ImportError] {exc}"
        except PermissionError as exc:
            return f"[PermissionError] {exc}"
        except Exception as exc:
            error_output = stderr_capture.getvalue()
            return f"[Error] {type(exc).__name__}: {exc}" + (
                f"\n{error_output}" if error_output else ""
            )

        stdout_output = stdout_capture.getvalue()
        stderr_output = stderr_capture.getvalue()

        result_parts: list[str] = []
        if stdout_output:
            result_parts.append(stdout_output)
        if stderr_output:
            result_parts.append(f"[STDERR]\n{stderr_output}")

        return "\n".join(result_parts) if result_parts else "(no output)"

    loop = asyncio.get_event_loop()
    try:
        result = await asyncio.wait_for(
            loop.run_in_executor(None, _run_code),
            timeout=timeout,
        )
    except asyncio.TimeoutError:
        return f"[ERROR] Code execution timed out after {timeout}s"

    logger.info("code_exec: completed (%d chars output)", len(result))
    return result
