"""
MiLyfe Brain - Download Route

Download workspace contents as a zip archive.
"""
from __future__ import annotations

import io
import logging
import os
import zipfile
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from config import settings

logger = logging.getLogger(__name__)

router = APIRouter()

# Directories and patterns to exclude from zip
_EXCLUDE_DIRS = {".git", "node_modules", "__pycache__", "venv", ".venv", ".mypy_cache"}
_MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB per file


@router.get("/workspace")
async def download_workspace() -> StreamingResponse:
    """Download the entire workspace as a zip file."""
    workspace = settings.workspace_path

    if not workspace.exists():
        raise HTTPException(status_code=404, detail="Workspace directory not found")

    buffer = io.BytesIO()

    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(workspace):
            # Filter out excluded directories in-place
            dirs[:] = [d for d in dirs if d not in _EXCLUDE_DIRS and not d.startswith(".")]

            root_path = Path(root)

            for filename in files:
                if filename.startswith("."):
                    continue

                filepath = root_path / filename

                try:
                    stat = filepath.stat()
                    if stat.st_size > _MAX_FILE_SIZE:
                        continue

                    rel_path = filepath.relative_to(workspace)
                    zf.write(filepath, arcname=str(rel_path))
                except (OSError, PermissionError):
                    continue

    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type="application/zip",
        headers={
            "Content-Disposition": "attachment; filename=workspace.zip",
        },
    )
