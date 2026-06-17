"""MiLyfe Brain — Workspace File Management Routes."""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException

from config import settings
from models.schemas import FileNode, WorkspaceTree

router = APIRouter()


@router.get("/tree", response_model=WorkspaceTree)
async def get_workspace_tree(max_depth: int = 3):
    """Get workspace directory tree."""
    root = Path(settings.workspace_dir)
    if not root.exists():
        root.mkdir(parents=True, exist_ok=True)

    tree = []
    total_files = 0
    total_dirs = 0

    def _scan(path: Path, depth: int) -> list[FileNode]:
        nonlocal total_files, total_dirs
        nodes = []
        try:
            entries = sorted(path.iterdir(), key=lambda x: (not x.is_dir(), x.name))
            for entry in entries:
                if entry.name.startswith(".") and entry.name not in (".milyfe",):
                    continue
                if entry.is_dir():
                    total_dirs += 1
                    children = _scan(entry, depth + 1) if depth < max_depth else []
                    nodes.append(FileNode(
                        name=entry.name,
                        path=str(entry.relative_to(root)),
                        is_dir=True,
                        children=children,
                    ))
                else:
                    total_files += 1
                    stat = entry.stat()
                    nodes.append(FileNode(
                        name=entry.name,
                        path=str(entry.relative_to(root)),
                        is_dir=False,
                        size=stat.st_size,
                        modified=datetime.fromtimestamp(stat.st_mtime),
                    ))
        except PermissionError:
            pass
        return nodes

    tree = _scan(root, 0)
    return WorkspaceTree(root=str(root), tree=tree, total_files=total_files, total_dirs=total_dirs)


@router.get("/read")
async def read_file(path: str):
    """Read a file from workspace."""
    file_path = Path(settings.workspace_dir) / path
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    if not str(file_path.resolve()).startswith(settings.workspace_dir):
        raise HTTPException(status_code=403, detail="Access denied")
    if file_path.stat().st_size > 5 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large (max 5MB)")

    try:
        content = file_path.read_text(encoding="utf-8", errors="replace")
        return {"path": path, "content": content, "size": len(content)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/recent")
async def recent_files(limit: int = 20):
    """Get recently modified files in workspace."""
    root = Path(settings.workspace_dir)
    if not root.exists():
        return {"files": []}

    files = []
    for f in root.rglob("*"):
        if f.is_file() and not any(p.startswith(".") for p in f.parts[len(root.parts):]):
            stat = f.stat()
            files.append({
                "path": str(f.relative_to(root)),
                "name": f.name,
                "size": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            })

    files.sort(key=lambda x: x["modified"], reverse=True)
    return {"files": files[:limit]}
