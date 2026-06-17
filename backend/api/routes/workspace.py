"""Workspace file tree and browsing routes."""

import os
from pathlib import Path

from fastapi import APIRouter, HTTPException

from config import settings

router = APIRouter()


@router.get("/tree")
async def get_workspace_tree(path: str = "", max_depth: int = 3):
    """Get workspace directory tree."""
    base_path = Path(settings.workspace_dir)
    target = base_path / path if path else base_path

    if not target.exists():
        raise HTTPException(status_code=404, detail="Path not found")

    tree = _build_tree(target, max_depth=max_depth, current_depth=0)
    return {"path": str(target), "tree": tree}


@router.get("/read")
async def read_file(path: str):
    """Read a workspace file."""
    base_path = Path(settings.workspace_dir)
    file_path = base_path / path

    # Security: ensure within workspace
    if not str(file_path.resolve()).startswith(str(base_path.resolve())):
        raise HTTPException(status_code=403, detail="Access denied")

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    if not file_path.is_file():
        raise HTTPException(status_code=400, detail="Not a file")

    # Size limit (5MB)
    if file_path.stat().st_size > 5 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large")

    try:
        content = file_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        content = f"[Binary file: {file_path.stat().st_size} bytes]"

    return {
        "path": path,
        "content": content,
        "size": file_path.stat().st_size,
        "modified": file_path.stat().st_mtime,
    }


@router.get("/recent")
async def get_recent_files(limit: int = 20):
    """Get recently modified files in workspace."""
    base_path = Path(settings.workspace_dir)

    if not base_path.exists():
        return {"files": []}

    files = []
    for f in base_path.rglob("*"):
        if f.is_file() and not _should_skip(f):
            files.append({
                "path": str(f.relative_to(base_path)),
                "size": f.stat().st_size,
                "modified": f.stat().st_mtime,
            })

    files.sort(key=lambda x: x["modified"], reverse=True)
    return {"files": files[:limit]}


def _build_tree(path: Path, max_depth: int, current_depth: int) -> list[dict]:
    """Recursively build directory tree."""
    if current_depth >= max_depth:
        return []

    items = []
    try:
        for entry in sorted(path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
            if _should_skip(entry):
                continue

            item = {
                "name": entry.name,
                "type": "directory" if entry.is_dir() else "file",
                "path": str(entry),
            }

            if entry.is_dir():
                item["children"] = _build_tree(entry, max_depth, current_depth + 1)
            else:
                item["size"] = entry.stat().st_size

            items.append(item)
    except PermissionError:
        pass

    return items


def _should_skip(path: Path) -> bool:
    """Check if path should be skipped in listing."""
    skip_names = {".git", "node_modules", "__pycache__", ".next", "venv", ".venv", ".cache"}
    return path.name in skip_names or path.name.startswith(".")
