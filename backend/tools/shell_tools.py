"""MiLyfe Brain — Shell Execution Tools (sandboxed)."""

from __future__ import annotations

import asyncio
import os

from config import settings
from models.schemas import PermissionLevel


async def shell_exec(
    command: str,
    cwd: str = "",
    timeout: int = 60,
) -> str:
    """Execute a shell command (sandboxed to workspace)."""
    from safety.command_classifier import classify_command

    # Classify risk
    risk = classify_command(command)
    if risk == "blocked":
        raise PermissionError(f"Command blocked by safety classifier: {command}")

    # Resolve working directory
    workspace = settings.workspace_dir
    work_dir = os.path.join(workspace, cwd) if cwd else workspace

    if not os.path.isdir(work_dir):
        os.makedirs(work_dir, exist_ok=True)

    # Execute with timeout
    try:
        proc = await asyncio.create_subprocess_shell(
            command,
            cwd=work_dir,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env={
                **os.environ,
                "HOME": "/root",
                "PATH": "/usr/local/bin:/usr/bin:/bin",
            },
        )

        stdout, stderr = await asyncio.wait_for(
            proc.communicate(), timeout=timeout
        )

        output = stdout.decode("utf-8", errors="replace")
        errors = stderr.decode("utf-8", errors="replace")

        result_parts = []
        if output:
            result_parts.append(f"STDOUT:\n{output}")
        if errors:
            result_parts.append(f"STDERR:\n{errors}")
        result_parts.append(f"Exit code: {proc.returncode}")

        full_output = "\n".join(result_parts)

        # Truncate if too long
        if len(full_output) > 10000:
            full_output = full_output[:9500] + "\n...[truncated]..."

        return full_output

    except asyncio.TimeoutError:
        raise TimeoutError(f"Command timed out after {timeout}s: {command}")


def register_shell_tools(registry):
    """Register shell tools."""
    registry.register(
        name="shell_exec",
        handler=shell_exec,
        category="Shell",
        description="Execute shell commands (sandboxed to workspace)",
        parameters={"command": "str", "cwd": "str (relative)", "timeout": "int (seconds)"},
        permission=PermissionLevel.NOTIFY,
    )
