"""Local filesystem browser routes."""

import os
from pathlib import Path

from fastapi import APIRouter, HTTPException

from config import settings

router = APIRouter()


@router.get("/browse")
async def browse_filesystem(path: str = "/"):
    """Browse the local filesystem (restricted to safe paths)."""
    allowed_roots = [settings.workspace_dir, os.path.expanduser("~/brain")]
    target = Path(path).resolve()

    # Security check
    if not any(str(target).startswith(str(Path(root).resolve())) for root in allowed_roots):
        raise HTTPException(status_code=403, detail="Access denied - path outside allowed directories")

    if not target.exists():
        raise HTTPException(status_code=404, detail="Path not found")

    if target.is_file():
        # Return file info
        return {
            "type": "file",
            "path": str(target),
            "name": target.name,
            "size": target.stat().st_size,
            "modified": target.stat().st_mtime,
        }

    # Directory listing
    items = []
    try:
        for entry in sorted(target.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
            if entry.name.startswith("."):
                continue
            items.append({
                "name": entry.name,
                "type": "directory" if entry.is_dir() else "file",
                "path": str(entry),
                "size": entry.stat().st_size if entry.is_file() else None,
            })
    except PermissionError:
        raise HTTPException(status_code=403, detail="Permission denied")

    return {"type": "directory", "path": str(target), "items": items}
