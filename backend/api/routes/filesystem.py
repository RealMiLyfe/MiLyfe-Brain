"""Filesystem API — Browse and read workspace files."""

import os

from fastapi import APIRouter, HTTPException, Query

from config import settings

router = APIRouter()


@router.get("/browse")
async def browse_directory(
    path: str = Query("", description="Relative path within workspace"),
) -> dict:
    """Browse a directory within the workspace."""
    workspace = settings.workspace_dir
    target = os.path.normpath(os.path.join(workspace, path))

    # Security: prevent directory traversal
    if not target.startswith(os.path.normpath(workspace)):
        raise HTTPException(status_code=403, detail="Access denied")

    if not os.path.exists(target):
        raise HTTPException(status_code=404, detail="Path not found")

    if not os.path.isdir(target):
        raise HTTPException(status_code=400, detail="Not a directory")

    entries = []
    try:
        for entry in sorted(os.listdir(target)):
            full_path = os.path.join(target, entry)
            rel_path = os.path.relpath(full_path, workspace)
            is_dir = os.path.isdir(full_path)
            entries.append({
                "name": entry,
                "path": rel_path,
                "type": "directory" if is_dir else "file",
                "size": os.path.getsize(full_path) if not is_dir else None,
            })
    except PermissionError:
        raise HTTPException(status_code=403, detail="Permission denied")

    return {"path": path, "entries": entries}


@router.get("/read")
async def read_file(
    path: str = Query(..., description="Relative path to file"),
) -> dict:
    """Read a file's content from the workspace."""
    workspace = settings.workspace_dir
    target = os.path.normpath(os.path.join(workspace, path))

    # Security: prevent directory traversal
    if not target.startswith(os.path.normpath(workspace)):
        raise HTTPException(status_code=403, detail="Access denied")

    if not os.path.exists(target):
        raise HTTPException(status_code=404, detail="File not found")

    if not os.path.isfile(target):
        raise HTTPException(status_code=400, detail="Not a file")

    # Check file size (max 1MB for API reading)
    size = os.path.getsize(target)
    if size > 1_048_576:
        raise HTTPException(status_code=413, detail="File too large (max 1MB)")

    try:
        with open(target, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Read error: {e}")

    return {"path": path, "content": content, "size": size}
