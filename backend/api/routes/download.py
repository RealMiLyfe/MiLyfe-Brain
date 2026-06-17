"""Workspace download (zip) route."""

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
    base_path = Path(settings.workspace_dir)

    if not base_path.exists():
        return {"error": "Workspace directory not found"}

    # Create zip in memory
    buffer = io.BytesIO()
    skip_dirs = {".git", "node_modules", "__pycache__", ".next", "venv", ".venv"}

    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_path in base_path.rglob("*"):
            # Skip excluded directories
            parts = file_path.relative_to(base_path).parts
            if any(part in skip_dirs for part in parts):
                continue

            if file_path.is_file() and file_path.stat().st_size < 10 * 1024 * 1024:
                arcname = str(file_path.relative_to(base_path))
                zf.write(file_path, arcname)

    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=workspace.zip"},
    )
