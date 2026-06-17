"""MiLyfe Brain — ChromaDB Vector Store (Pure httpx REST API)."""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

import httpx
import structlog

from config import settings

logger = structlog.get_logger()


class VectorStore:
    """ChromaDB REST API client (pure httpx, no chromadb Python client)."""

    def __init__(self):
        self._base_url = settings.chroma_url
        self._collections_cache: Dict[str, str] = {}

    async def _get_or_create_collection(self, name: str) -> str:
        """Get or create a collection, return its ID."""
        if name in self._collections_cache:
            return self._collections_cache[name]

        async with httpx.AsyncClient(timeout=10.0) as client:
            # Try to get existing
            resp = await client.get(
                f"{self._base_url}/api/v1/collections/{name}"
            )
            if resp.status_code == 200:
                col_id = resp.json().get("id", "")
                self._collections_cache[name] = col_id
                return col_id

            # Create new
            resp = await client.post(
                f"{self._base_url}/api/v1/collections",
                json={"name": name, "get_or_create": True},
            )
            if resp.status_code in (200, 201):
                col_id = resp.json().get("id", "")
                self._collections_cache[name] = col_id
                return col_id

            raise RuntimeError(f"Failed to get/create collection '{name}': {resp.status_code}")

    async def add_documents(
        self,
        collection: str,
        documents: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        ids: Optional[List[str]] = None,
    ):
        """Add documents to a collection."""
        col_id = await self._get_or_create_collection(collection)

        if not ids:
            ids = [str(uuid.uuid4()) for _ in documents]
        if not metadatas:
            metadatas = [{} for _ in documents]

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{self._base_url}/api/v1/collections/{col_id}/add",
                json={
                    "ids": ids,
                    "documents": documents,
                    "metadatas": metadatas,
                },
            )
            if resp.status_code not in (200, 201):
                logger.error("vector_add_failed", status=resp.status_code,
                             body=resp.text[:200])
                raise RuntimeError(f"ChromaDB add failed: {resp.status_code}")

    async def query(
        self,
        collection: str,
        query_text: str,
        n_results: int = 5,
        where: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Query a collection for similar documents."""
        try:
            col_id = await self._get_or_create_collection(collection)
        except Exception:
            return []

        payload: Dict[str, Any] = {
            "query_texts": [query_text],
            "n_results": n_results,
        }
        if where:
            payload["where"] = where

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{self._base_url}/api/v1/collections/{col_id}/query",
                json=payload,
            )
            if resp.status_code != 200:
                return []

            data = resp.json()
            results = []
            docs = data.get("documents", [[]])[0]
            metas = data.get("metadatas", [[]])[0]
            ids = data.get("ids", [[]])[0]
            distances = data.get("distances", [[]])[0]

            for i in range(len(docs)):
                results.append({
                    "id": ids[i] if i < len(ids) else "",
                    "document": docs[i] if i < len(docs) else "",
                    "metadata": metas[i] if i < len(metas) else {},
                    "distance": distances[i] if i < len(distances) else 0.0,
                })

            return results

    async def list_documents(
        self, collection: str, limit: int = 100
    ) -> Dict[str, Any]:
        """List documents in a collection."""
        try:
            col_id = await self._get_or_create_collection(collection)
        except Exception:
            return {"documents": [], "total": 0}

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{self._base_url}/api/v1/collections/{col_id}/get",
                json={"limit": limit, "include": ["metadatas", "documents"]},
            )
            if resp.status_code != 200:
                return {"documents": [], "total": 0}

            data = resp.json()
            docs = []
            for i, doc_id in enumerate(data.get("ids", [])):
                meta = data.get("metadatas", [])[i] if i < len(data.get("metadatas", [])) else {}
                docs.append({
                    "id": doc_id,
                    "filename": meta.get("filename", "unknown"),
                    "doc_id": meta.get("doc_id", doc_id),
                })

            # Deduplicate by doc_id
            seen = set()
            unique_docs = []
            for d in docs:
                did = d.get("doc_id", d["id"])
                if did not in seen:
                    seen.add(did)
                    unique_docs.append(d)

            return {"documents": unique_docs, "total": len(unique_docs)}

    async def delete_documents(self, collection: str, doc_id: str):
        """Delete documents by doc_id metadata."""
        try:
            col_id = await self._get_or_create_collection(collection)
        except Exception:
            return

        async with httpx.AsyncClient(timeout=10.0) as client:
            # Get IDs with this doc_id
            resp = await client.post(
                f"{self._base_url}/api/v1/collections/{col_id}/get",
                json={"where": {"doc_id": doc_id}, "include": []},
            )
            if resp.status_code != 200:
                return

            ids = resp.json().get("ids", [])
            if not ids:
                return

            # Delete them
            await client.post(
                f"{self._base_url}/api/v1/collections/{col_id}/delete",
                json={"ids": ids},
            )

    async def count(self, collection: str) -> int:
        """Get document count in a collection."""
        try:
            col_id = await self._get_or_create_collection(collection)
        except Exception:
            return 0

        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                f"{self._base_url}/api/v1/collections/{col_id}/count"
            )
            if resp.status_code == 200:
                return resp.json()
            return 0


# Singleton
vector_store = VectorStore()
