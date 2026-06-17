"""MiLyfe Brain — ChromaDB Vector Store (Pure httpx REST Client).

Communicates with ChromaDB via its REST API using httpx.
Implements a circuit breaker pattern to gracefully handle
ChromaDB unavailability without blocking the application.

ADR: docs/decisions/0002-pure-httpx-for-chromadb.md
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import httpx
import structlog

from config import settings

logger = structlog.get_logger("vector_store")


# ═══════════════════════════════════════════════════════════════════════
# CIRCUIT BREAKER
# ═══════════════════════════════════════════════════════════════════════


@dataclass
class CircuitBreaker:
    """Simple circuit breaker to skip calls when ChromaDB is unavailable.

    States:
        CLOSED  — normal operation, requests pass through
        OPEN    — service is down, requests are skipped
        HALF_OPEN — testing if service recovered
    """

    failure_threshold: int = 3
    recovery_timeout: float = 30.0  # seconds before retrying

    _failure_count: int = field(default=0, init=False)
    _state: str = field(default="closed", init=False)
    _last_failure_time: float = field(default=0.0, init=False)

    @property
    def state(self) -> str:
        """Get current circuit state, auto-transitioning to half_open if timeout elapsed."""
        if self._state == "open":
            if time.time() - self._last_failure_time >= self.recovery_timeout:
                self._state = "half_open"
        return self._state

    @property
    def is_available(self) -> bool:
        """Whether requests should be attempted."""
        return self.state != "open"

    def record_success(self) -> None:
        """Record a successful request — resets the breaker."""
        self._failure_count = 0
        self._state = "closed"

    def record_failure(self) -> None:
        """Record a failed request — may trip the breaker."""
        self._failure_count += 1
        self._last_failure_time = time.time()
        if self._failure_count >= self.failure_threshold:
            self._state = "open"
            logger.warning(
                "circuit_breaker_opened",
                failures=self._failure_count,
                recovery_timeout=self.recovery_timeout,
            )

    def reset(self) -> None:
        """Manually reset the breaker."""
        self._failure_count = 0
        self._state = "closed"
        self._last_failure_time = 0.0


# ═══════════════════════════════════════════════════════════════════════
# VECTOR STORE CLIENT
# ═══════════════════════════════════════════════════════════════════════


class VectorStore:
    """ChromaDB REST API client with circuit breaker protection.

    All operations are non-blocking and will gracefully degrade
    if ChromaDB is unreachable (returning empty results).
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: float = 10.0,
        failure_threshold: int = 3,
        recovery_timeout: float = 30.0,
    ) -> None:
        self._base_url = (base_url or settings.chromadb_url).rstrip("/")
        self._timeout = timeout
        self._circuit_breaker = CircuitBreaker(
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
        )
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Lazily create the httpx async client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                timeout=self._timeout,
                headers={"Content-Type": "application/json"},
            )
        return self._client

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    @property
    def is_available(self) -> bool:
        """Whether the vector store is currently considered available."""
        return self._circuit_breaker.is_available

    # ─── Collection Management ────────────────────────────────────────

    async def _ensure_collection(self, collection_name: str) -> Optional[str]:
        """Get or create a collection, returning its ID or None on failure."""
        client = await self._get_client()
        try:
            response = await client.post(
                "/api/v1/collections",
                json={
                    "name": collection_name,
                    "get_or_create": True,
                },
            )
            response.raise_for_status()
            data = response.json()
            self._circuit_breaker.record_success()
            return data.get("id")
        except (httpx.HTTPError, httpx.TimeoutException) as exc:
            self._circuit_breaker.record_failure()
            logger.warning("chromadb_ensure_collection_failed", error=str(exc))
            return None

    # ─── Public API ───────────────────────────────────────────────────

    async def add_documents(
        self,
        collection_name: str,
        documents: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        ids: Optional[List[str]] = None,
    ) -> bool:
        """Add documents to a ChromaDB collection.

        Args:
            collection_name: Target collection name.
            documents: List of text documents to embed and store.
            metadatas: Optional metadata dicts for each document.
            ids: Optional IDs; auto-generated if not provided.

        Returns:
            True if documents were added successfully, False otherwise.
        """
        if not self._circuit_breaker.is_available:
            logger.debug("chromadb_skipped_circuit_open", operation="add_documents")
            return False

        if not documents:
            return True

        # Generate IDs if not provided
        if ids is None:
            ids = [str(uuid.uuid4()) for _ in documents]

        # Ensure metadatas length matches documents
        if metadatas is None:
            metadatas = [{} for _ in documents]

        collection_id = await self._ensure_collection(collection_name)
        if collection_id is None:
            return False

        client = await self._get_client()
        try:
            response = await client.post(
                f"/api/v1/collections/{collection_id}/add",
                json={
                    "ids": ids,
                    "documents": documents,
                    "metadatas": metadatas,
                },
            )
            response.raise_for_status()
            self._circuit_breaker.record_success()
            logger.debug(
                "chromadb_documents_added",
                collection=collection_name,
                count=len(documents),
            )
            return True
        except (httpx.HTTPError, httpx.TimeoutException) as exc:
            self._circuit_breaker.record_failure()
            logger.warning(
                "chromadb_add_failed",
                collection=collection_name,
                error=str(exc),
            )
            return False

    async def query(
        self,
        collection_name: str,
        query_texts: List[str],
        n_results: int = 5,
        where: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Query a collection for similar documents.

        Args:
            collection_name: Collection to search.
            query_texts: Query strings for similarity search.
            n_results: Maximum number of results per query.
            where: Optional metadata filter.

        Returns:
            List of result dicts with ids, documents, distances, metadatas.
            Returns empty list if unavailable.
        """
        if not self._circuit_breaker.is_available:
            logger.debug("chromadb_skipped_circuit_open", operation="query")
            return []

        if not query_texts:
            return []

        collection_id = await self._ensure_collection(collection_name)
        if collection_id is None:
            return []

        client = await self._get_client()
        try:
            payload: Dict[str, Any] = {
                "query_texts": query_texts,
                "n_results": n_results,
            }
            if where:
                payload["where"] = where

            response = await client.post(
                f"/api/v1/collections/{collection_id}/query",
                json=payload,
            )
            response.raise_for_status()
            self._circuit_breaker.record_success()

            data = response.json()
            # Format results for easy consumption
            results = []
            for i, query_text in enumerate(query_texts):
                result = {
                    "query": query_text,
                    "ids": data.get("ids", [[]])[i] if i < len(data.get("ids", [])) else [],
                    "documents": data.get("documents", [[]])[i] if i < len(data.get("documents", [])) else [],
                    "distances": data.get("distances", [[]])[i] if i < len(data.get("distances", [])) else [],
                    "metadatas": data.get("metadatas", [[]])[i] if i < len(data.get("metadatas", [])) else [],
                }
                results.append(result)

            logger.debug(
                "chromadb_query_success",
                collection=collection_name,
                queries=len(query_texts),
                results_per_query=n_results,
            )
            return results
        except (httpx.HTTPError, httpx.TimeoutException) as exc:
            self._circuit_breaker.record_failure()
            logger.warning(
                "chromadb_query_failed",
                collection=collection_name,
                error=str(exc),
            )
            return []

    async def delete_collection(self, collection_name: str) -> bool:
        """Delete an entire collection.

        Args:
            collection_name: Name of the collection to delete.

        Returns:
            True if deleted successfully, False otherwise.
        """
        if not self._circuit_breaker.is_available:
            logger.debug("chromadb_skipped_circuit_open", operation="delete_collection")
            return False

        client = await self._get_client()
        try:
            # First get the collection to find its ID
            response = await client.get(f"/api/v1/collections/{collection_name}")
            if response.status_code == 404:
                # Collection doesn't exist — nothing to delete
                return True
            response.raise_for_status()
            collection_id = response.json().get("id")

            # Delete by name
            response = await client.delete(f"/api/v1/collections/{collection_name}")
            response.raise_for_status()
            self._circuit_breaker.record_success()
            logger.info("chromadb_collection_deleted", collection=collection_name)
            return True
        except (httpx.HTTPError, httpx.TimeoutException) as exc:
            self._circuit_breaker.record_failure()
            logger.warning(
                "chromadb_delete_collection_failed",
                collection=collection_name,
                error=str(exc),
            )
            return False

    async def list_collections(self) -> List[Dict[str, Any]]:
        """List all available collections.

        Returns:
            List of collection info dicts, or empty list if unavailable.
        """
        if not self._circuit_breaker.is_available:
            logger.debug("chromadb_skipped_circuit_open", operation="list_collections")
            return []

        client = await self._get_client()
        try:
            response = await client.get("/api/v1/collections")
            response.raise_for_status()
            self._circuit_breaker.record_success()
            collections = response.json()
            logger.debug("chromadb_list_collections", count=len(collections))
            return collections
        except (httpx.HTTPError, httpx.TimeoutException) as exc:
            self._circuit_breaker.record_failure()
            logger.warning("chromadb_list_collections_failed", error=str(exc))
            return []


# ═══════════════════════════════════════════════════════════════════════
# MODULE-LEVEL SINGLETON
# ═══════════════════════════════════════════════════════════════════════

vector_store = VectorStore()
