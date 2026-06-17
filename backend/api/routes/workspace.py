"""Workspace API — File tree browsing."""

import os
from typing import List

from fastapi import APIRouter

from config import settings

router = APIRouter()


@router.get("/tree")
async def get_workspace_tree() -> dict:
    """Get the workspace file tree (max depth 3)."""
    workspace = settings.workspace_dir
    if not os.path.exists(workspace):
        return {"tree": [], "root": workspace}

    tree = _build_tree(workspace, max_depth=3)
    return {"tree": tree, "root": workspace}


def _build_tree(path: str, max_depth: int, current_depth: int = 0) -> List[dict]:
    """Recursively build a file tree structure."""
    if current_depth >= max_depth:
        return []

    items = []
    ignore = {".git", "__pycache__", "node_modules", ".venv", ".env"}

    try:
        entries = sorted(os.listdir(path))
    except PermissionError:
        return []

    for entry in entries:
        if entry in ignore or entry.startswith("."):
            continue

        full_path = os.path.join(path, entry)
        rel_path = os.path.relpath(full_path, settings.workspace_dir)

        if os.path.isdir(full_path):
            children = _build_tree(full_path, max_depth, current_depth + 1)
            items.append({
                "name": entry,
                "path": rel_path,
                "type": "directory",
                "children": children,
            })
        else:
            try:
                size = os.path.getsize(full_path)
            except OSError:
                size = 0
            items.append({
                "name": entry,
                "path": rel_path,
                "type": "file",
                "size": size,
            })

    return items
