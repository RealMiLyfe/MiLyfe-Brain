"""MiLyfe Brain — Document Upload + Semantic Search Routes."""

from __future__ import annotations

import uuid
from typing import List

import structlog
from fastapi import APIRouter, File, HTTPException, UploadFile

from models.schemas import DocumentResult, DocumentSearch

logger = structlog.get_logger()
router = APIRouter()


@router.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    """Upload a PDF/TXT/MD file and store in ChromaDB."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    content = await file.read()
    filename = file.filename.lower()

    # Extract text based on file type
    if filename.endswith(".pdf"):
        try:
            from PyPDF2 import PdfReader
            import io
            reader = PdfReader(io.BytesIO(content))
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to parse PDF: {e}")
    elif filename.endswith((".txt", ".md", ".py", ".js", ".ts", ".yaml", ".yml", ".json")):
        text = content.decode("utf-8", errors="replace")
    else:
        raise HTTPException(status_code=400, detail="Unsupported file type. Use PDF, TXT, MD, or code files.")

    if not text.strip():
        raise HTTPException(status_code=400, detail="Document is empty")

    # Chunk the text
    chunks = _chunk_text(text, chunk_size=1000, overlap=200)

    # Store in ChromaDB
    try:
        from memory.vector_store import vector_store
        doc_id = str(uuid.uuid4())
        await vector_store.add_documents(
            collection="documents",
            documents=chunks,
            metadatas=[{"filename": file.filename, "doc_id": doc_id, "chunk_idx": i} for i in range(len(chunks))],
            ids=[f"{doc_id}_chunk_{i}" for i in range(len(chunks))],
        )

        return {
            "id": doc_id,
            "filename": file.filename,
            "chunks": len(chunks),
            "total_chars": len(text),
        }
    except Exception as e:
        logger.error("document_upload_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Storage failed: {e}")


@router.post("/search", response_model=List[DocumentResult])
async def search_documents(data: DocumentSearch):
    """Semantic search across uploaded documents."""
    try:
        from memory.vector_store import vector_store
        results = await vector_store.query(
            collection=data.collection or "documents",
            query_text=data.query,
            n_results=data.limit,
        )
        return [
            DocumentResult(
                id=r["id"],
                content=r["document"],
                metadata=r.get("metadata", {}),
                distance=r.get("distance", 0.0),
            )
            for r in results
        ]
    except Exception as e:
        logger.error("document_search_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/")
async def list_documents():
    """List all uploaded documents."""
    try:
        from memory.vector_store import vector_store
        docs = await vector_store.list_documents(collection="documents")
        return docs
    except Exception as e:
        return {"documents": [], "error": str(e)}


@router.delete("/{doc_id}")
async def delete_document(doc_id: str):
    """Delete a document and its chunks from ChromaDB."""
    try:
        from memory.vector_store import vector_store
        await vector_store.delete_documents(collection="documents", doc_id=doc_id)
        return {"detail": "Document deleted", "id": doc_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> list[str]:
    """Split text into overlapping chunks."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        if chunk.strip():
            chunks.append(chunk.strip())
        start = end - overlap
    return chunks or [text[:chunk_size]]
