"""Document upload and semantic search routes."""

import uuid
from datetime import datetime

from fastapi import APIRouter, HTTPException, UploadFile, File

from models.schemas import DocumentResponse, DocumentSearchRequest, DocumentSearchResult

router = APIRouter()


@router.post("/upload", response_model=DocumentResponse)
async def upload_document(file: UploadFile = File(...)):
    """Upload a document (PDF/TXT/MD) and store in ChromaDB."""
    from memory.database import db
    from memory.vector_store import vector_store

    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    content_type = file.content_type or "text/plain"
    content = await file.read()

    # Extract text based on content type
    if content_type == "application/pdf" or file.filename.endswith(".pdf"):
        from PyPDF2 import PdfReader
        import io
        reader = PdfReader(io.BytesIO(content))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
    else:
        text = content.decode("utf-8", errors="replace")

    # Chunk the text
    chunks = _chunk_text(text, chunk_size=1000, overlap=100)

    # Store in ChromaDB
    doc_id = str(uuid.uuid4())
    await vector_store.add_documents(
        collection="documents",
        ids=[f"{doc_id}_{i}" for i in range(len(chunks))],
        documents=chunks,
        metadatas=[{"filename": file.filename, "doc_id": doc_id, "chunk_index": i} for i in range(len(chunks))],
    )

    # Store metadata in SQLite
    now = datetime.utcnow().isoformat()
    await db.execute(
        """INSERT INTO documents (id, filename, content_type, chunk_count, created_at)
           VALUES (?, ?, ?, ?, ?)""",
        (doc_id, file.filename, content_type, len(chunks), now),
    )

    return DocumentResponse(
        id=doc_id,
        filename=file.filename,
        content_type=content_type,
        chunk_count=len(chunks),
        created_at=now,
    )


@router.post("/search", response_model=list[DocumentSearchResult])
async def search_documents(request: DocumentSearchRequest):
    """Semantic search across uploaded documents."""
    from memory.vector_store import vector_store

    results = await vector_store.query(
        collection="documents",
        query_text=request.query,
        n_results=request.limit,
    )

    return [
        DocumentSearchResult(
            id=r["id"],
            content=r["document"],
            metadata=r.get("metadata", {}),
            score=r.get("distance", 0.0),
        )
        for r in results
    ]


@router.get("/", response_model=list[DocumentResponse])
async def list_documents():
    """List all uploaded documents."""
    from memory.database import db

    rows = await db.fetch_all("SELECT * FROM documents ORDER BY created_at DESC")
    return [
        DocumentResponse(
            id=row["id"],
            filename=row["filename"],
            content_type=row["content_type"],
            chunk_count=row["chunk_count"],
            created_at=row["created_at"],
        )
        for row in rows
    ]


@router.delete("/{doc_id}")
async def delete_document(doc_id: str):
    """Delete a document from ChromaDB and SQLite."""
    from memory.database import db
    from memory.vector_store import vector_store

    await vector_store.delete_by_metadata("documents", {"doc_id": doc_id})
    await db.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
    return {"message": "Document deleted", "id": doc_id}


def _chunk_text(text: str, chunk_size: int = 1000, overlap: int = 100) -> list[str]:
    """Split text into overlapping chunks."""
    if not text:
        return [""]

    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        if chunk.strip():
            chunks.append(chunk)
        start = end - overlap

    return chunks or [""]
