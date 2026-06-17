"""Download API — Workspace export as zip."""

import io
import os
import zipfile

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from config import settings

router = APIRouter()


@router.get("/workspace")
async def download_workspace() -> StreamingResponse:
    """Download the entire workspace as a zip file."""
    workspace = settings.workspace_dir
    ignore = {".git", "__pycache__", "node_modules", ".venv"}

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(workspace):
            # Filter ignored directories
            dirs[:] = [d for d in dirs if d not in ignore]

            for filename in files:
                filepath = os.path.join(root, filename)
                arcname = os.path.relpath(filepath, workspace)
                try:
                    zf.write(filepath, arcname)
                except (PermissionError, OSError):
                    pass

    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type="application/zip",
        headers={
            "Content-Disposition": "attachment; filename=workspace.zip"
        },
    )
