"""Documents API — Document upload, search, and management."""

import os
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from memory.database import get_db

router = APIRouter()

# In-memory document store (backed by filesystem)
_UPLOAD_DIR = os.path.join(settings.workspace_dir, ".documents")


class SearchRequest(BaseModel):
    """Document search request."""
    query: str
    limit: int = 10


@router.post("/upload")
async def upload_document(file: UploadFile = File(...)) -> dict:
    """Upload a document to the workspace."""
    os.makedirs(_UPLOAD_DIR, exist_ok=True)

    doc_id = str(uuid.uuid4())
    filename = file.filename or "untitled"
    filepath = os.path.join(_UPLOAD_DIR, f"{doc_id}_{filename}")

    content = await file.read()
    with open(filepath, "wb") as f:
        f.write(content)

    return {
        "id": doc_id,
        "filename": filename,
        "size": len(content),
        "path": filepath,
        "uploaded_at": datetime.utcnow().isoformat(),
    }


@router.post("/search")
async def search_documents(body: SearchRequest) -> dict:
    """Search documents using vector store."""
    try:
        from memory.vector_store import vector_store
        results = await vector_store.search(body.query, n=body.limit)
        return {"results": results, "query": body.query}
    except Exception as e:
        return {"results": [], "query": body.query, "error": str(e)}


@router.get("/")
async def list_documents() -> dict:
    """List all uploaded documents."""
    if not os.path.exists(_UPLOAD_DIR):
        return {"documents": []}

    docs = []
    for filename in os.listdir(_UPLOAD_DIR):
        filepath = os.path.join(_UPLOAD_DIR, filename)
        if os.path.isfile(filepath):
            docs.append({
                "id": filename.split("_")[0] if "_" in filename else filename,
                "filename": "_".join(filename.split("_")[1:]) if "_" in filename else filename,
                "size": os.path.getsize(filepath),
                "path": filepath,
            })

    return {"documents": docs}


@router.delete("/{doc_id}")
async def delete_document(doc_id: str) -> dict:
    """Delete a document by ID."""
    if not os.path.exists(_UPLOAD_DIR):
        raise HTTPException(status_code=404, detail="Document not found")

    for filename in os.listdir(_UPLOAD_DIR):
        if filename.startswith(doc_id):
            filepath = os.path.join(_UPLOAD_DIR, filename)
            os.remove(filepath)
            return {"message": "Document deleted", "id": doc_id}

    raise HTTPException(status_code=404, detail="Document not found")
