"""MiLyfe Brain — File Tools (read, write, delete, list)."""

from __future__ import annotations

import os
from pathlib import Path

from config import settings
from models.schemas import PermissionLevel


def _safe_path(path: str) -> Path:
    """Resolve path within workspace sandbox."""
    workspace = Path(settings.workspace_dir)
    target = (workspace / path).resolve()
    if not str(target).startswith(str(workspace.resolve())):
        raise PermissionError(f"Path outside workspace: {path}")
    return target


async def file_read(path: str, encoding: str = "utf-8") -> str:
    """Read file contents."""
    target = _safe_path(path)
    if not target.exists():
        raise FileNotFoundError(f"File not found: {path}")
    if target.stat().st_size > 5 * 1024 * 1024:
        raise ValueError("File too large (max 5MB)")
    return target.read_text(encoding=encoding, errors="replace")


async def file_write(path: str, content: str, encoding: str = "utf-8") -> str:
    """Write content to a file (creates dirs if needed)."""
    target = _safe_path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding=encoding)
    return f"Written {len(content)} chars to {path}"


async def file_delete(path: str) -> str:
    """Delete a file."""
    target = _safe_path(path)
    if not target.exists():
        raise FileNotFoundError(f"File not found: {path}")
    if target.is_dir():
        import shutil
        shutil.rmtree(target)
        return f"Deleted directory: {path}"
    target.unlink()
    return f"Deleted: {path}"


async def file_list(path: str = ".", recursive: bool = False) -> str:
    """List directory contents."""
    target = _safe_path(path)
    if not target.exists():
        raise FileNotFoundError(f"Directory not found: {path}")
    if not target.is_dir():
        raise ValueError(f"Not a directory: {path}")

    entries = []
    if recursive:
        for item in sorted(target.rglob("*")):
            rel = item.relative_to(target)
            if any(p.startswith(".") for p in rel.parts):
                continue
            prefix = "D " if item.is_dir() else "F "
            size = f" ({item.stat().st_size}B)" if item.is_file() else ""
            entries.append(f"{prefix}{rel}{size}")
    else:
        for item in sorted(target.iterdir()):
            if item.name.startswith("."):
                continue
            prefix = "D " if item.is_dir() else "F "
            size = f" ({item.stat().st_size}B)" if item.is_file() else ""
            entries.append(f"{prefix}{item.name}{size}")

    return "\n".join(entries) if entries else "(empty directory)"


def register_file_tools(registry):
    """Register file tools with the registry."""
    registry.register(
        name="file_read",
        handler=file_read,
        category="File",
        description="Read file contents",
        parameters={"path": "str", "encoding": "str (default utf-8)"},
        permission=PermissionLevel.FREE,
    )
    registry.register(
        name="file_write",
        handler=file_write,
        category="File",
        description="Write/create files",
        parameters={"path": "str", "content": "str"},
        permission=PermissionLevel.NOTIFY,
    )
    registry.register(
        name="file_delete",
        handler=file_delete,
        category="File",
        description="Delete files or directories",
        parameters={"path": "str"},
        permission=PermissionLevel.APPROVE,
    )
    registry.register(
        name="file_list",
        handler=file_list,
        category="File",
        description="List directory contents",
        parameters={"path": "str", "recursive": "bool"},
        permission=PermissionLevel.FREE,
    )
