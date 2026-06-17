"""Shell execution tools for MiLyfe Brain.

Provides sandboxed shell command execution with timeout and output limits.
Integrates with the command classifier for safety checks.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

from config import settings
from safety.command_classifier import classify_command, RISK_BLOCKED, RISK_DANGEROUS

logger = logging.getLogger(__name__)

MAX_OUTPUT_CHARS = 50000


async def shell_exec(
    command: str,
    cwd: Optional[str] = None,
    timeout: int = 30,
) -> str:
    """Execute a shell command and return combined stdout/stderr.

    Performs safety classification before execution. Commands classified
    as "blocked" are rejected. "Dangerous" commands are logged prominently.

    Args:
        command: The shell command string to execute.
        cwd: Working directory for the command. Defaults to workspace_dir.
        timeout: Maximum execution time in seconds (default 30, max 300).

    Returns:
        Combined stdout and stderr output, truncated if exceeding MAX_OUTPUT_CHARS.
    """
    work_dir = cwd or settings.workspace_dir

    # Enforce max timeout
    timeout = min(timeout, 300)

    # Safety classification
    classification = classify_command(command)
    risk_level = classification["risk_level"]
    reasons = classification.get("reasons", [])

    if risk_level == RISK_BLOCKED:
        reason_str = "; ".join(str(r) for r in reasons)
        logger.warning("BLOCKED shell command: %r — %s", command, reason_str)
        return f"[BLOCKED] Command rejected for safety: {reason_str}"

    if risk_level == RISK_DANGEROUS:
        reason_str = "; ".join(str(r) for r in reasons)
        logger.warning("DANGEROUS shell command (proceeding with approval): %r — %s", command, reason_str)

    logger.info("shell_exec: command=%r cwd=%s timeout=%d risk=%s", command, work_dir, timeout, risk_level)

    try:
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=work_dir,
        )

        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            return f"[ERROR] Command timed out after {timeout}s: {command}"

    except OSError as exc:
        logger.error("shell_exec: OS error: %s", exc)
        return f"[ERROR] Failed to execute command: {exc}"

    stdout = stdout_bytes.decode("utf-8", errors="replace")
    stderr = stderr_bytes.decode("utf-8", errors="replace")

    # Combine output
    output_parts: list[str] = []
    if stdout.strip():
        output_parts.append(stdout)
    if stderr.strip():
        output_parts.append(f"[STDERR]\n{stderr}")

    output = "\n".join(output_parts) if output_parts else "(no output)"

    # Include exit code if non-zero
    exit_code = process.returncode
    if exit_code != 0:
        output = f"[Exit code: {exit_code}]\n{output}"

    # Truncate if necessary
    if len(output) > MAX_OUTPUT_CHARS:
        output = output[:MAX_OUTPUT_CHARS] + f"\n\n[TRUNCATED — output exceeded {MAX_OUTPUT_CHARS} chars]"

    logger.info("shell_exec: completed (exit=%d, %d chars)", exit_code or 0, len(output))
    return output
