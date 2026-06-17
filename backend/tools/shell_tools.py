"""Shell Tools — Sandboxed shell command execution."""

import asyncio
import os
from pathlib import Path

from config import settings


async def shell_exec(command: str, cwd: str = None, timeout: int = 60) -> str:
    """Execute a shell command with safety checks.

    Args:
        command: Shell command to execute
        cwd: Working directory (defaults to workspace)
        timeout: Max execution time in seconds
    """
    from safety.command_classifier import classify_command

    # Safety check
    risk = classify_command(command)
    if risk == "blocked":
        raise PermissionError(f"Command blocked by safety classifier: {command[:100]}")

    # Resolve working directory
    work_dir = cwd or settings.workspace_dir
    work_dir_path = Path(work_dir)
    if not work_dir_path.exists():
        work_dir_path.mkdir(parents=True, exist_ok=True)

    try:
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(work_dir_path),
            env={**os.environ, "HOME": os.path.expanduser("~")},
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=timeout
            )
        except asyncio.TimeoutError:
            process.kill()
            return f"Command timed out after {timeout}s: {command[:100]}"

        output = ""
        if stdout:
            output += stdout.decode("utf-8", errors="replace")
        if stderr:
            output += "\n[STDERR]\n" + stderr.decode("utf-8", errors="replace")

        output += f"\n[Exit code: {process.returncode}]"

        # Truncate if too long
        if len(output) > 50000:
            output = output[:25000] + "\n...[truncated]...\n" + output[-25000:]

        return output

    except Exception as e:
        return f"Error executing command: {str(e)}"


def register_shell_tools(registry):
    """Register shell tools with the tool registry."""
    registry.register("shell_exec", "Execute shell command (sandboxed)", shell_exec, permission="notify",
                      params={"command": "Shell command", "cwd": "Working directory", "timeout": "Timeout in seconds"})
