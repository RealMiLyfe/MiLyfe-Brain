"""MiLyfe Brain — Workspace Download Routes."""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from config import settings

router = APIRouter()


@router.get("/workspace")
async def download_workspace():
    """Download workspace as a zip file."""
    root = Path(settings.workspace_dir)
    if not root.exists():
        return {"detail": "No workspace data"}

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_path in root.rglob("*"):
            if file_path.is_file():
                # Skip hidden files and large files
                rel = file_path.relative_to(root)
                if any(p.startswith(".") for p in rel.parts):
                    continue
                if file_path.stat().st_size > 50 * 1024 * 1024:
                    continue
                zf.write(file_path, arcname=str(rel))

    buffer.seek(0)
    return StreamingResponse(
        buffer,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=workspace.zip"},
    )
