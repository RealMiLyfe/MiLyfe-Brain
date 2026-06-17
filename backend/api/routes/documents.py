"""
MiLyfe Brain - Documents Route

Document upload, chunking, embedding in ChromaDB, and semantic search.
"""
from __future__ import annotations

import hashlib
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from models.schemas import DocumentResult, DocumentSearch

logger = logging.getLogger(__name__)

router = APIRouter()


class DocumentInfo(BaseModel):
    """Document metadata returned from listing."""
    id: str
    filename: str
    collection: str
    chunk_count: int = 0
    created_at: Optional[str] = None


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    collection: str = "default",
) -> Dict[str, Any]:
    """Upload a file, chunk it, and embed in ChromaDB."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    content = await file.read()
    text = content.decode("utf-8", errors="replace")

    # Chunk the document
    chunks = _chunk_text(text, chunk_size=1000, overlap=200)
    doc_id = hashlib.sha256(content).hexdigest()[:16]

    # Store in vector store
    try:
        from memory.vector_store import vector_store

        ids = [f"{doc_id}_chunk_{i}" for i in range(len(chunks))]
        metadatas = [
            {
                "filename": file.filename,
                "chunk_index": i,
                "doc_id": doc_id,
                "created_at": datetime.utcnow().isoformat(),
            }
            for i in range(len(chunks))
        ]

        await vector_store.add_documents(
            collection=collection,
            documents=chunks,
            metadatas=metadatas,
            ids=ids,
        )

        return {
            "doc_id": doc_id,
            "filename": file.filename,
            "collection": collection,
            "chunks": len(chunks),
            "total_chars": len(text),
        }

    except Exception as e:
        logger.error("Document upload failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.post("/search", response_model=List[DocumentResult])
async def search_documents(body: DocumentSearch) -> List[DocumentResult]:
    """Semantic search across documents in ChromaDB."""
    try:
        from memory.vector_store import vector_store

        results = await vector_store.query(
            collection=body.collection,
            query_text=body.query,
            n_results=body.n_results,
            where=body.filters if body.filters else None,
        )

        documents: List[DocumentResult] = []
        if results and "documents" in results:
            docs = results.get("documents", [[]])[0]
            metas = results.get("metadatas", [[]])[0]
            distances = results.get("distances", [[]])[0]
            ids = results.get("ids", [[]])[0]

            for i, doc in enumerate(docs):
                score = 1.0 - (distances[i] if i < len(distances) else 0.0)
                meta = metas[i] if i < len(metas) else {}
                documents.append(DocumentResult(
                    id=ids[i] if i < len(ids) else str(i),
                    content=doc,
                    score=score,
                    metadata=meta,
                    source=meta.get("filename"),
                ))

        return documents

    except Exception as e:
        logger.error("Document search failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.get("/", response_model=List[DocumentInfo])
async def list_documents(
    collection: str = "default",
) -> List[DocumentInfo]:
    """List documents in a collection."""
    try:
        from memory.vector_store import vector_store

        results = await vector_store.list_documents(collection=collection)

        # Group by doc_id
        doc_map: Dict[str, DocumentInfo] = {}
        if results and "metadatas" in results:
            for i, meta in enumerate(results.get("metadatas", [])):
                doc_id = meta.get("doc_id", f"unknown_{i}")
                if doc_id not in doc_map:
                    doc_map[doc_id] = DocumentInfo(
                        id=doc_id,
                        filename=meta.get("filename", "unknown"),
                        collection=collection,
                        chunk_count=0,
                        created_at=meta.get("created_at"),
                    )
                doc_map[doc_id].chunk_count += 1

        return list(doc_map.values())

    except Exception as e:
        logger.error("Document list failed: %s", e)
        return []


@router.delete("/{doc_id}")
async def delete_document(doc_id: str, collection: str = "default") -> Dict[str, str]:
    """Delete a document and all its chunks from ChromaDB."""
    try:
        from memory.vector_store import vector_store

        await vector_store.delete_documents(collection=collection, doc_id=doc_id)
        return {"status": "deleted", "doc_id": doc_id}

    except Exception as e:
        logger.error("Document delete failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Delete failed: {str(e)}")


def _chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
    """Split text into overlapping chunks."""
    if len(text) <= chunk_size:
        return [text]

    chunks: List[str] = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        if chunk.strip():
            chunks.append(chunk)
        start += chunk_size - overlap

    return chunks
