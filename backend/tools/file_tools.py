"""File operation tools for MiLyfe Brain.

All file operations are sandboxed within WORKSPACE_DIR via _safe_path().
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

from config import settings

logger = logging.getLogger(__name__)

WORKSPACE_DIR = Path(settings.workspace_dir).resolve()


def _safe_path(path: str) -> Path:
    """Validate and resolve a path to ensure it stays within WORKSPACE_DIR.

    Args:
        path: Relative or absolute file path from the user.

    Returns:
        Resolved Path object guaranteed to be inside the workspace.

    Raises:
        PermissionError: If the resolved path escapes the workspace directory.
    """
    # If the path is relative, join it with workspace
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = WORKSPACE_DIR / candidate

    resolved = candidate.resolve()

    # Verify the resolved path is within the workspace
    try:
        resolved.relative_to(WORKSPACE_DIR)
    except ValueError:
        raise PermissionError(
            f"Path traversal denied: '{path}' resolves outside workspace ({WORKSPACE_DIR})"
        )

    return resolved


async def file_read(path: str) -> str:
    """Read the contents of a file.

    Args:
        path: Relative or absolute file path within the workspace.

    Returns:
        The full text content of the file.
    """
    target = _safe_path(path)

    if not target.exists():
        raise FileNotFoundError(f"File not found: {target}")
    if not target.is_file():
        raise IsADirectoryError(f"Path is a directory, not a file: {target}")

    content = target.read_text(encoding="utf-8")
    logger.info("file_read: %s (%d bytes)", target, len(content))
    return content


async def file_write(path: str, content: str) -> str:
    """Write content to a file, creating parent directories if needed.

    Args:
        path: Relative or absolute file path within the workspace.
        content: Text content to write.

    Returns:
        Confirmation message with byte count and path.
    """
    target = _safe_path(path)

    # Ensure parent directories exist
    target.parent.mkdir(parents=True, exist_ok=True)

    target.write_text(content, encoding="utf-8")
    byte_count = len(content.encode("utf-8"))
    logger.info("file_write: %s (%d bytes)", target, byte_count)
    return f"Written {byte_count} bytes to {target}"


async def file_delete(path: str) -> str:
    """Delete a file from the workspace.

    Args:
        path: Relative or absolute file path within the workspace.

    Returns:
        Confirmation message.
    """
    target = _safe_path(path)

    if not target.exists():
        raise FileNotFoundError(f"File not found: {target}")
    if not target.is_file():
        raise IsADirectoryError(f"Cannot delete a directory with file_delete: {target}")

    target.unlink()
    logger.info("file_delete: %s", target)
    return f"Deleted {target}"


async def file_list(path: str, recursive: bool = False) -> str:
    """List files and directories at the given path.

    Args:
        path: Directory path within the workspace.
        recursive: If True, list all entries recursively.

    Returns:
        Formatted directory listing with type indicators.
    """
    target = _safe_path(path)

    if not target.exists():
        raise FileNotFoundError(f"Directory not found: {target}")
    if not target.is_dir():
        raise NotADirectoryError(f"Path is not a directory: {target}")

    entries: list[str] = []

    if recursive:
        for item in sorted(target.rglob("*")):
            relative = item.relative_to(target)
            prefix = "📁 " if item.is_dir() else "📄 "
            entries.append(f"{prefix}{relative}")
    else:
        for item in sorted(target.iterdir()):
            prefix = "📁 " if item.is_dir() else "📄 "
            size = ""
            if item.is_file():
                size = f"  ({item.stat().st_size} bytes)"
            entries.append(f"{prefix}{item.name}{size}")

    if not entries:
        return f"Empty directory: {target}"

    header = f"Directory listing: {target}\n{'─' * 40}\n"
    logger.info("file_list: %s (recursive=%s, %d entries)", target, recursive, len(entries))
    return header + "\n".join(entries)
