"""File Tools — read, write, delete, list."""

import os
from pathlib import Path

from config import settings


def _safe_path(path: str) -> Path:
    """Ensure path is within allowed directories."""
    base = Path(settings.workspace_dir).resolve()
    target = (base / path).resolve() if not os.path.isabs(path) else Path(path).resolve()

    allowed = [base, Path.home() / "brain"]
    if not any(str(target).startswith(str(a)) for a in allowed):
        raise PermissionError(f"Access denied: {path} is outside workspace")

    return target


async def file_read(path: str) -> str:
    """Read file contents."""
    target = _safe_path(path)
    if not target.exists():
        raise FileNotFoundError(f"File not found: {path}")
    if not target.is_file():
        raise ValueError(f"Not a file: {path}")
    if target.stat().st_size > 5 * 1024 * 1024:
        raise ValueError("File too large (>5MB)")

    try:
        return target.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return f"[Binary file: {target.stat().st_size} bytes]"


async def file_write(path: str, content: str) -> str:
    """Write content to a file (creates directories as needed)."""
    target = _safe_path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return f"Written {len(content)} bytes to {path}"


async def file_delete(path: str) -> str:
    """Delete a file."""
    target = _safe_path(path)
    if not target.exists():
        raise FileNotFoundError(f"File not found: {path}")
    target.unlink()
    return f"Deleted: {path}"


async def file_list(path: str = ".", recursive: bool = False) -> str:
    """List directory contents."""
    target = _safe_path(path)
    if not target.exists():
        raise FileNotFoundError(f"Directory not found: {path}")
    if not target.is_dir():
        raise ValueError(f"Not a directory: {path}")

    skip = {".git", "node_modules", "__pycache__", ".next", "venv", ".venv"}
    items = []

    if recursive:
        for entry in target.rglob("*"):
            if any(part in skip for part in entry.relative_to(target).parts):
                continue
            rel_path = str(entry.relative_to(target))
            type_marker = "D" if entry.is_dir() else "F"
            items.append(f"[{type_marker}] {rel_path}")
    else:
        for entry in sorted(target.iterdir()):
            if entry.name in skip:
                continue
            type_marker = "D" if entry.is_dir() else "F"
            size = f" ({entry.stat().st_size}B)" if entry.is_file() else ""
            items.append(f"[{type_marker}] {entry.name}{size}")

    return "\n".join(items) if items else "(empty directory)"


def register_file_tools(registry):
    """Register file tools with the tool registry."""
    registry.register("file_read", "Read file contents", file_read, permission="free",
                      params={"path": "File path to read"})
    registry.register("file_write", "Write/create a file", file_write, permission="notify",
                      params={"path": "File path", "content": "File content"})
    registry.register("file_delete", "Delete a file", file_delete, permission="approve",
                      params={"path": "File path to delete"})
    registry.register("file_list", "List directory contents", file_list, permission="free",
                      params={"path": "Directory path", "recursive": "Boolean for recursive listing"})
