"""
MiLyfe Brain - Filesystem Route

File system browsing: directory listing and file content reading.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, Query

from config import settings

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/list")
async def list_directory(
    path: str = Query(default=".", description="Relative path within workspace"),
) -> Dict[str, Any]:
    """Get a directory listing."""
    workspace = settings.workspace_path
    target = (workspace / path).resolve()

    # Security check
    if not str(target).startswith(str(workspace)):
        raise HTTPException(status_code=403, detail="Path outside workspace")

    if not target.exists():
        raise HTTPException(status_code=404, detail="Path not found")

    if not target.is_dir():
        raise HTTPException(status_code=400, detail="Path is not a directory")

    entries: List[Dict[str, Any]] = []
    try:
        for entry in sorted(target.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
            if entry.name.startswith("."):
                continue

            try:
                stat = entry.stat()
                entries.append({
                    "name": entry.name,
                    "path": str(entry.relative_to(workspace)),
                    "is_dir": entry.is_dir(),
                    "size": stat.st_size if not entry.is_dir() else None,
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                })
            except OSError:
                continue
    except PermissionError:
        raise HTTPException(status_code=403, detail="Permission denied")

    return {
        "path": path,
        "entries": entries,
        "count": len(entries),
    }


@router.get("/read")
async def read_file(
    path: str = Query(..., description="Relative path within workspace"),
    encoding: str = Query(default="utf-8"),
) -> Dict[str, Any]:
    """Read file content."""
    workspace = settings.workspace_path
    file_path = (workspace / path).resolve()

    # Security check
    if not str(file_path).startswith(str(workspace)):
        raise HTTPException(status_code=403, detail="Path outside workspace")

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    if file_path.is_dir():
        raise HTTPException(status_code=400, detail="Path is a directory, use /list endpoint")

    # Size limit: 5MB
    stat = file_path.stat()
    if stat.st_size > 5 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large (max 5MB)")

    try:
        content = file_path.read_text(encoding=encoding, errors="replace")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read file: {str(e)}")

    return {
        "path": path,
        "content": content,
        "size": stat.st_size,
        "encoding": encoding,
        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
    }
