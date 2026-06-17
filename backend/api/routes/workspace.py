"""
MiLyfe Brain - Workspace Route

Workspace directory tree browsing and file reading.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query

from config import settings
from models.schemas import FileNode, WorkspaceTree

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/tree", response_model=WorkspaceTree)
async def get_workspace_tree(
    max_depth: int = Query(default=3, ge=1, le=10),
) -> WorkspaceTree:
    """Get the workspace directory tree."""
    workspace = settings.workspace_path

    if not workspace.exists():
        return WorkspaceTree(root=str(workspace), tree=[], total_files=0, total_dirs=0)

    total_files = 0
    total_dirs = 0

    def build_tree(path: Path, depth: int) -> List[FileNode]:
        nonlocal total_files, total_dirs

        if depth <= 0:
            return []

        nodes: List[FileNode] = []
        try:
            entries = sorted(path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
        except PermissionError:
            return []

        for entry in entries:
            # Skip hidden files and common ignore patterns
            if entry.name.startswith(".") or entry.name in (
                "node_modules", "__pycache__", ".git", "venv", ".venv",
            ):
                continue

            if entry.is_dir():
                total_dirs += 1
                children = build_tree(entry, depth - 1)
                nodes.append(FileNode(
                    name=entry.name,
                    path=str(entry.relative_to(workspace)),
                    is_dir=True,
                    children=children,
                ))
            else:
                total_files += 1
                try:
                    stat = entry.stat()
                    size = stat.st_size
                    modified = datetime.fromtimestamp(stat.st_mtime)
                except OSError:
                    size = None
                    modified = None

                nodes.append(FileNode(
                    name=entry.name,
                    path=str(entry.relative_to(workspace)),
                    is_dir=False,
                    size=size,
                    modified=modified,
                ))

        return nodes

    tree = build_tree(workspace, max_depth)

    return WorkspaceTree(
        root=str(workspace),
        tree=tree,
        total_files=total_files,
        total_dirs=total_dirs,
    )


@router.get("/read")
async def read_file(
    path: str = Query(..., description="Relative path within workspace"),
    max_size: int = Query(default=1048576, description="Max file size in bytes"),
) -> Dict[str, Any]:
    """Read file content from the workspace."""
    workspace = settings.workspace_path
    file_path = (workspace / path).resolve()

    # Security: ensure path is within workspace
    if not str(file_path).startswith(str(workspace)):
        raise HTTPException(status_code=403, detail="Path outside workspace")

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    if file_path.is_dir():
        raise HTTPException(status_code=400, detail="Path is a directory")

    stat = file_path.stat()
    if stat.st_size > max_size:
        raise HTTPException(
            status_code=413,
            detail=f"File too large ({stat.st_size} bytes, max {max_size})",
        )

    try:
        content = file_path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Read error: {str(e)}")

    return {
        "path": path,
        "content": content,
        "size": stat.st_size,
        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        "lines": content.count("\n") + 1,
    }


@router.get("/recent")
async def recent_files(
    limit: int = Query(default=20, ge=1, le=100),
) -> List[Dict[str, Any]]:
    """Get recently modified files in the workspace."""
    workspace = settings.workspace_path

    if not workspace.exists():
        return []

    files: List[Dict[str, Any]] = []

    for root, _dirs, filenames in os.walk(workspace):
        root_path = Path(root)
        # Skip hidden and ignored dirs
        if any(part.startswith(".") for part in root_path.relative_to(workspace).parts):
            continue
        if any(p in root_path.parts for p in ("node_modules", "__pycache__", "venv")):
            continue

        for fname in filenames:
            if fname.startswith("."):
                continue
            filepath = root_path / fname
            try:
                stat = filepath.stat()
                files.append({
                    "path": str(filepath.relative_to(workspace)),
                    "name": fname,
                    "size": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "modified_ts": stat.st_mtime,
                })
            except OSError:
                continue

    # Sort by modification time descending
    files.sort(key=lambda f: f["modified_ts"], reverse=True)

    # Remove timestamp field and limit
    result = []
    for f in files[:limit]:
        f.pop("modified_ts", None)
        result.append(f)

    return result
