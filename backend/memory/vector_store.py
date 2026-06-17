"""
MiLyfe Brain - Vector Store (ChromaDB REST Client)

ChromaDB REST client using httpx for document embedding and retrieval.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import httpx

from config import settings

logger = logging.getLogger(__name__)


class VectorStore:
    """ChromaDB REST client for document storage and semantic search."""

    def __init__(self, base_url: Optional[str] = None) -> None:
        self._base_url = base_url or settings.chroma_url
        self._collections_cache: Dict[str, str] = {}

    def _client(self) -> httpx.AsyncClient:
        """Create an httpx async client."""
        return httpx.AsyncClient(
            base_url=self._base_url,
            timeout=30.0,
        )

    async def _get_or_create_collection(self, name: str) -> str:
        """Get or create a ChromaDB collection, return collection ID."""
        if name in self._collections_cache:
            return self._collections_cache[name]

        async with self._client() as client:
            # Try to get existing collection
            try:
                resp = await client.get(f"/api/v1/collections/{name}")
                if resp.status_code == 200:
                    data = resp.json()
                    collection_id = data.get("id", name)
                    self._collections_cache[name] = collection_id
                    return collection_id
            except Exception:
                pass

            # Create collection
            resp = await client.post(
                "/api/v1/collections",
                json={"name": name, "get_or_create": True},
            )

            if resp.status_code in (200, 201):
                data = resp.json()
                collection_id = data.get("id", name)
                self._collections_cache[name] = collection_id
                return collection_id
            else:
                logger.error(
                    "Failed to create collection %s: %s %s",
                    name, resp.status_code, resp.text,
                )
                raise RuntimeError(f"Failed to create collection: {resp.status_code}")

    async def add_documents(
        self,
        collection: str,
        documents: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        ids: Optional[List[str]] = None,
    ) -> None:
        """Add documents to a collection with optional metadata and IDs."""
        collection_id = await self._get_or_create_collection(collection)

        if ids is None:
            import uuid
            ids = [str(uuid.uuid4()) for _ in documents]

        if metadatas is None:
            metadatas = [{} for _ in documents]

        payload: Dict[str, Any] = {
            "ids": ids,
            "documents": documents,
            "metadatas": metadatas,
        }

        async with self._client() as client:
            resp = await client.post(
                f"/api/v1/collections/{collection_id}/add",
                json=payload,
            )

            if resp.status_code not in (200, 201):
                logger.error(
                    "Failed to add documents to %s: %s %s",
                    collection, resp.status_code, resp.text,
                )
                raise RuntimeError(f"Failed to add documents: {resp.status_code}")

        logger.debug("Added %d documents to collection %s", len(documents), collection)

    async def query(
        self,
        collection: str,
        query_text: str,
        n_results: int = 5,
        where: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Query a collection for similar documents."""
        collection_id = await self._get_or_create_collection(collection)

        payload: Dict[str, Any] = {
            "query_texts": [query_text],
            "n_results": n_results,
        }
        if where:
            payload["where"] = where

        async with self._client() as client:
            resp = await client.post(
                f"/api/v1/collections/{collection_id}/query",
                json=payload,
            )

            if resp.status_code != 200:
                logger.error(
                    "Query failed on %s: %s %s",
                    collection, resp.status_code, resp.text,
                )
                return {"documents": [[]], "metadatas": [[]], "distances": [[]], "ids": [[]]}

            return resp.json()

    async def list_documents(
        self,
        collection: str,
        limit: int = 100,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """List documents in a collection."""
        collection_id = await self._get_or_create_collection(collection)

        async with self._client() as client:
            resp = await client.post(
                f"/api/v1/collections/{collection_id}/get",
                json={"limit": limit, "offset": offset, "include": ["metadatas", "documents"]},
            )

            if resp.status_code != 200:
                logger.error(
                    "List failed on %s: %s %s",
                    collection, resp.status_code, resp.text,
                )
                return {"ids": [], "documents": [], "metadatas": []}

            return resp.json()

    async def delete_documents(
        self,
        collection: str,
        doc_id: str,
    ) -> None:
        """Delete all chunks belonging to a document ID."""
        collection_id = await self._get_or_create_collection(collection)

        async with self._client() as client:
            resp = await client.post(
                f"/api/v1/collections/{collection_id}/delete",
                json={"where": {"doc_id": doc_id}},
            )

            if resp.status_code not in (200, 204):
                logger.error(
                    "Delete failed on %s for doc %s: %s %s",
                    collection, doc_id, resp.status_code, resp.text,
                )
                raise RuntimeError(f"Failed to delete document: {resp.status_code}")

        logger.debug("Deleted document %s from collection %s", doc_id, collection)

    async def count(self, collection: str) -> int:
        """Get the number of documents in a collection."""
        collection_id = await self._get_or_create_collection(collection)

        async with self._client() as client:
            resp = await client.get(
                f"/api/v1/collections/{collection_id}/count",
            )

            if resp.status_code == 200:
                return resp.json()
            return 0


# Singleton instance
vector_store = VectorStore()
