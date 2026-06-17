"""MiLyfe Brain — Local Filesystem Browser Routes."""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import APIRouter, HTTPException

from config import settings

router = APIRouter()

# Additional safe paths (beyond workspace)
SAFE_PATHS = [Path(settings.workspace_dir), Path.home() / "brain"]


def _is_safe_path(path: Path) -> bool:
    """Check if path is within allowed directories."""
    resolved = path.resolve()
    return any(str(resolved).startswith(str(safe.resolve())) for safe in SAFE_PATHS if safe.exists())


@router.get("/list")
async def list_directory(path: str = "."):
    """List directory contents."""
    target = Path(settings.workspace_dir) / path if not Path(path).is_absolute() else Path(path)

    if not _is_safe_path(target):
        raise HTTPException(status_code=403, detail="Access denied: path outside workspace")
    if not target.exists():
        raise HTTPException(status_code=404, detail="Directory not found")
    if not target.is_dir():
        raise HTTPException(status_code=400, detail="Path is not a directory")

    entries = []
    for entry in sorted(target.iterdir(), key=lambda x: (not x.is_dir(), x.name)):
        stat = entry.stat()
        entries.append({
            "name": entry.name,
            "path": str(entry),
            "is_dir": entry.is_dir(),
            "size": stat.st_size if entry.is_file() else 0,
            "modified": stat.st_mtime,
        })

    return {"path": str(target), "entries": entries}


@router.get("/read")
async def read_file(path: str):
    """Read file contents."""
    file_path = Path(settings.workspace_dir) / path if not Path(path).is_absolute() else Path(path)

    if not _is_safe_path(file_path):
        raise HTTPException(status_code=403, detail="Access denied")
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    if file_path.stat().st_size > 5 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large")

    try:
        content = file_path.read_text(encoding="utf-8", errors="replace")
        return {"path": str(file_path), "content": content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
