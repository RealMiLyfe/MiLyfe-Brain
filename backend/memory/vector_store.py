"""ChromaDB Vector Store — Pure httpx REST API client.

No chromadb Python client for vector operations — all direct REST calls.
"""

from typing import Optional

import httpx
import structlog

from config import settings

logger = structlog.get_logger()


class VectorStore:
    """ChromaDB REST API client via httpx."""

    def __init__(self):
        self.base_url = settings.chroma_url

    async def _get_or_create_collection(self, name: str) -> str:
        """Get or create a collection, return its ID."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Try to get existing
            try:
                resp = await client.get(f"{self.base_url}/api/v1/collections/{name}")
                if resp.status_code == 200:
                    return resp.json().get("id", name)
            except Exception:
                pass

            # Create new
            resp = await client.post(
                f"{self.base_url}/api/v1/collections",
                json={"name": name, "metadata": {"hnsw:space": "cosine"}},
            )
            if resp.status_code in (200, 201):
                return resp.json().get("id", name)

            # Already exists
            resp = await client.get(f"{self.base_url}/api/v1/collections/{name}")
            if resp.status_code == 200:
                return resp.json().get("id", name)

            raise Exception(f"Failed to get/create collection: {name}")

    async def add_documents(
        self,
        collection: str,
        ids: list[str],
        documents: list[str],
        metadatas: Optional[list[dict]] = None,
    ) -> None:
        """Add documents to a collection."""
        try:
            collection_id = await self._get_or_create_collection(collection)

            async with httpx.AsyncClient(timeout=30.0) as client:
                payload = {
                    "ids": ids,
                    "documents": documents,
                }
                if metadatas:
                    payload["metadatas"] = metadatas

                resp = await client.post(
                    f"{self.base_url}/api/v1/collections/{collection_id}/add",
                    json=payload,
                )
                if resp.status_code not in (200, 201):
                    logger.warning("ChromaDB add failed", status=resp.status_code, body=resp.text[:200])

        except Exception as e:
            logger.error("Vector store add failed", error=str(e))

    async def query(
        self,
        collection: str,
        query_text: str,
        n_results: int = 5,
        where: Optional[dict] = None,
    ) -> list[dict]:
        """Query documents by semantic similarity."""
        try:
            collection_id = await self._get_or_create_collection(collection)

            async with httpx.AsyncClient(timeout=15.0) as client:
                payload = {
                    "query_texts": [query_text],
                    "n_results": n_results,
                }
                if where:
                    payload["where"] = where

                resp = await client.post(
                    f"{self.base_url}/api/v1/collections/{collection_id}/query",
                    json=payload,
                )

                if resp.status_code != 200:
                    logger.warning("ChromaDB query failed", status=resp.status_code)
                    return []

                data = resp.json()
                results = []

                ids = data.get("ids", [[]])[0]
                documents = data.get("documents", [[]])[0]
                metadatas = data.get("metadatas", [[]])[0]
                distances = data.get("distances", [[]])[0]

                for i in range(len(ids)):
                    results.append({
                        "id": ids[i],
                        "document": documents[i] if i < len(documents) else "",
                        "metadata": metadatas[i] if i < len(metadatas) else {},
                        "distance": distances[i] if i < len(distances) else 0.0,
                    })

                return results

        except Exception as e:
            logger.error("Vector store query failed", error=str(e))
            return []

    async def delete_by_metadata(self, collection: str, where: dict) -> None:
        """Delete documents matching metadata filter."""
        try:
            collection_id = await self._get_or_create_collection(collection)

            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    f"{self.base_url}/api/v1/collections/{collection_id}/delete",
                    json={"where": where},
                )
                if resp.status_code not in (200, 204):
                    logger.warning("ChromaDB delete failed", status=resp.status_code)

        except Exception as e:
            logger.error("Vector store delete failed", error=str(e))

    async def count(self, collection: str) -> int:
        """Get document count in a collection."""
        try:
            collection_id = await self._get_or_create_collection(collection)

            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(
                    f"{self.base_url}/api/v1/collections/{collection_id}/count"
                )
                if resp.status_code == 200:
                    return resp.json()
        except Exception:
            pass
        return 0


# Global instance
vector_store = VectorStore()
