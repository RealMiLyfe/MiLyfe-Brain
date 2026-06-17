"""
MiLyfe Brain - File System Tools

Safe file operations with path traversal protection.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

from config import settings
from models.schemas import PermissionLevel

if TYPE_CHECKING:
    from tools.registry import ToolRegistry


def _safe_path(path: str) -> Path:
    """Resolve path within workspace, raise PermissionError on traversal attempts."""
    workspace = settings.workspace_path
    resolved = (workspace / path).resolve()
    if not str(resolved).startswith(str(workspace)):
        raise PermissionError(
            f"Path traversal detected: '{path}' resolves outside workspace"
        )
    return resolved


def file_read(path: str, encoding: str = "utf-8") -> str:
    """Read a file from the workspace.

    Args:
        path: Relative path within workspace.
        encoding: File encoding (default utf-8).

    Returns:
        File contents as string.
    """
    target = _safe_path(path)
    if not target.exists():
        raise FileNotFoundError(f"File not found: {path}")
    if not target.is_file():
        raise IsADirectoryError(f"Path is a directory: {path}")
    content = target.read_text(encoding=encoding)
    return content


def file_write(path: str, content: str, encoding: str = "utf-8") -> str:
    """Write content to a file in the workspace.

    Args:
        path: Relative path within workspace.
        content: Content to write.
        encoding: File encoding (default utf-8).

    Returns:
        Confirmation message with bytes written.
    """
    target = _safe_path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding=encoding)
    size = target.stat().st_size
    return f"Written {size} bytes to {path}"


def file_delete(path: str) -> str:
    """Delete a file from the workspace.

    Args:
        path: Relative path within workspace.

    Returns:
        Confirmation message.
    """
    target = _safe_path(path)
    if not target.exists():
        raise FileNotFoundError(f"File not found: {path}")
    if target.is_dir():
        raise IsADirectoryError(f"Cannot delete directory with file_delete: {path}")
    target.unlink()
    return f"Deleted: {path}"


def file_list(path: str = ".", recursive: bool = False) -> str:
    """List files and directories in a workspace path.

    Args:
        path: Relative directory path within workspace.
        recursive: Whether to list recursively.

    Returns:
        Formatted directory listing.
    """
    target = _safe_path(path)
    if not target.exists():
        raise FileNotFoundError(f"Directory not found: {path}")
    if not target.is_dir():
        raise NotADirectoryError(f"Path is not a directory: {path}")

    entries = []
    if recursive:
        for root, dirs, files in os.walk(target):
            # Skip hidden and common non-essential dirs
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            rel_root = Path(root).relative_to(target)
            for f in sorted(files):
                entries.append(str(rel_root / f) if str(rel_root) != "." else f)
            if len(entries) > 500:
                entries.append("... (truncated at 500 entries)")
                break
    else:
        for item in sorted(target.iterdir()):
            prefix = "[DIR]  " if item.is_dir() else "[FILE] "
            entries.append(f"{prefix}{item.name}")

    if not entries:
        return f"Empty directory: {path}"
    return "\n".join(entries)


def register_file_tools(registry: ToolRegistry) -> None:
    """Register file tools with the tool registry."""
    registry.register(
        name="file_read",
        handler=file_read,
        category="filesystem",
        description="Read a file from the workspace.",
        parameters={
            "path": {"type": "string", "description": "Relative path within workspace", "required": True},
            "encoding": {"type": "string", "description": "File encoding", "default": "utf-8"},
        },
        permission=PermissionLevel.SAFE,
        returns="File contents as string",
    )
    registry.register(
        name="file_write",
        handler=file_write,
        category="filesystem",
        description="Write content to a file in the workspace.",
        parameters={
            "path": {"type": "string", "description": "Relative path within workspace", "required": True},
            "content": {"type": "string", "description": "Content to write", "required": True},
            "encoding": {"type": "string", "description": "File encoding", "default": "utf-8"},
        },
        permission=PermissionLevel.MODERATE,
        returns="Confirmation with bytes written",
    )
    registry.register(
        name="file_delete",
        handler=file_delete,
        category="filesystem",
        description="Delete a file from the workspace.",
        parameters={
            "path": {"type": "string", "description": "Relative path within workspace", "required": True},
        },
        permission=PermissionLevel.DESTRUCTIVE,
        returns="Confirmation message",
    )
    registry.register(
        name="file_list",
        handler=file_list,
        category="filesystem",
        description="List files and directories in a workspace path.",
        parameters={
            "path": {"type": "string", "description": "Directory path", "default": "."},
            "recursive": {"type": "boolean", "description": "List recursively", "default": False},
        },
        permission=PermissionLevel.SAFE,
        returns="Formatted directory listing",
    )
