"""
MiLyfe Brain - Shell Execution Tools

Safe shell command execution with timeout and output capture.
"""
from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from config import settings
from models.schemas import PermissionLevel

if TYPE_CHECKING:
    from tools.registry import ToolRegistry

# Commands that are never allowed
BLOCKED_COMMANDS = [
    "rm -rf /",
    "mkfs",
    "dd if=",
    ":(){:|:&};:",
    "chmod -R 777 /",
    "shutdown",
    "reboot",
    "halt",
    "init 0",
    "init 6",
]

# Patterns that require extra scrutiny
DANGEROUS_PATTERNS = [
    "rm -rf",
    "rm -fr",
    "sudo",
    "> /dev/",
    "curl | sh",
    "wget | sh",
    "curl | bash",
    "wget | bash",
]

MAX_OUTPUT_LENGTH = 10000


def _check_command_safety(command: str) -> str:
    """Check command for dangerous patterns.

    Returns:
        Empty string if safe, warning message if dangerous.
    """
    cmd_lower = command.lower().strip()

    for blocked in BLOCKED_COMMANDS:
        if blocked in cmd_lower:
            return f"BLOCKED: Command contains forbidden pattern '{blocked}'"

    warnings = []
    for pattern in DANGEROUS_PATTERNS:
        if pattern in cmd_lower:
            warnings.append(f"Warning: command contains '{pattern}'")

    return "; ".join(warnings)


async def shell_exec(command: str, cwd: str = "", timeout: int = 60) -> str:
    """Execute a shell command with safety checks and timeout.

    Args:
        command: Shell command to execute.
        cwd: Working directory (relative to workspace). Defaults to workspace root.
        timeout: Execution timeout in seconds (max 300).

    Returns:
        Formatted output with stdout, stderr, and exit code.
    """
    # Safety check
    safety_result = _check_command_safety(command)
    if safety_result.startswith("BLOCKED"):
        return safety_result

    # Resolve working directory
    workspace = settings.workspace_path
    if cwd:
        work_dir = (workspace / cwd).resolve()
        if not str(work_dir).startswith(str(workspace)):
            return "Error: Working directory resolves outside workspace"
        if not work_dir.is_dir():
            return f"Error: Working directory does not exist: {cwd}"
    else:
        work_dir = workspace

    # Clamp timeout
    timeout = min(max(timeout, 1), 300)

    try:
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(work_dir),
        )
        stdout, stderr = await asyncio.wait_for(
            process.communicate(), timeout=timeout
        )
    except asyncio.TimeoutError:
        try:
            process.kill()
            await process.wait()
        except ProcessLookupError:
            pass
        return f"Error: Command timed out after {timeout}s\nCommand: {command}"
    except Exception as e:
        return f"Error executing command: {type(e).__name__}: {e}"

    # Format output
    stdout_text = stdout.decode("utf-8", errors="replace").strip()
    stderr_text = stderr.decode("utf-8", errors="replace").strip()
    exit_code = process.returncode

    parts = []
    if stdout_text:
        parts.append(f"STDOUT:\n{stdout_text}")
    if stderr_text:
        parts.append(f"STDERR:\n{stderr_text}")
    parts.append(f"EXIT CODE: {exit_code}")

    if safety_result:
        parts.insert(0, safety_result)

    output = "\n\n".join(parts)

    # Truncate if too long
    if len(output) > MAX_OUTPUT_LENGTH:
        output = output[:MAX_OUTPUT_LENGTH] + f"\n\n... (truncated at {MAX_OUTPUT_LENGTH} chars)"

    return output


def register_shell_tools(registry: ToolRegistry) -> None:
    """Register shell tools with the tool registry."""
    registry.register(
        name="shell_exec",
        handler=shell_exec,
        category="shell",
        description="Execute a shell command with safety checks and timeout.",
        parameters={
            "command": {"type": "string", "description": "Shell command to execute", "required": True},
            "cwd": {"type": "string", "description": "Working directory relative to workspace", "default": ""},
            "timeout": {"type": "integer", "description": "Timeout in seconds (max 300)", "default": 60},
        },
        permission=PermissionLevel.MODERATE,
        returns="Command output with stdout, stderr, and exit code",
    )
