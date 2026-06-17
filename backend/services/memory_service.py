"""
MiLyfe Brain - Memory Service

Wraps ChromaDB vector store for agent memory operations.
Provides recall (semantic search) and store (embedding + persist) functionality.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional
from uuid import uuid4

logger = logging.getLogger(__name__)

# ChromaDB collection name for agent memories
_COLLECTION_NAME = "agent_memories"


async def recall_memories(
    query: str,
    agent_role: Optional[str] = None,
    limit: int = 5,
) -> str:
    """
    Recall relevant memories using semantic search.

    Args:
        query: Search query text.
        agent_role: Optional filter by agent role.
        limit: Maximum number of memories to return.

    Returns:
        Formatted string of recalled memories, or empty string if none found.
    """
    try:
        import httpx

        from config import settings

        # Query ChromaDB
        chroma_url = settings.chroma_url.rstrip("/")

        # Build where filter
        where_filter = None
        if agent_role:
            where_filter = {"agent_role": agent_role}

        payload = {
            "query_texts": [query],
            "n_results": limit,
        }
        if where_filter:
            payload["where"] = where_filter

        async with httpx.AsyncClient(timeout=10) as client:
            # First ensure collection exists
            await client.post(
                f"{chroma_url}/api/v1/collections",
                json={"name": _COLLECTION_NAME, "get_or_create": True},
            )

            # Get collection ID
            resp = await client.get(
                f"{chroma_url}/api/v1/collections/{_COLLECTION_NAME}",
            )
            if resp.status_code != 200:
                logger.debug("Collection not found, no memories available")
                return ""

            collection_data = resp.json()
            collection_id = collection_data.get("id", "")

            # Query the collection
            resp = await client.post(
                f"{chroma_url}/api/v1/collections/{collection_id}/query",
                json=payload,
            )

            if resp.status_code != 200:
                logger.warning("ChromaDB query failed: %s", resp.status_code)
                return ""

            results = resp.json()
            documents = results.get("documents", [[]])[0]
            metadatas = results.get("metadatas", [[]])[0]

            if not documents:
                return ""

            # Format results
            memories = []
            for i, (doc, meta) in enumerate(zip(documents, metadatas), 1):
                role = meta.get("agent_role", "unknown") if meta else "unknown"
                memories.append(f"[Memory {i}] ({role}): {doc}")

            return "\n".join(memories)

    except Exception as e:
        logger.debug("Memory recall failed (ChromaDB may be unavailable): %s", e)
        return await _fallback_recall(query, agent_role, limit)


async def store_memory(
    content: str,
    agent_role: str,
    playbook_id: Optional[str] = None,
    importance: float = 0.5,
) -> Optional[str]:
    """
    Store a memory in both ChromaDB (vector) and SQLite (structured).

    Args:
        content: Memory content text.
        agent_role: Role of the agent storing the memory.
        playbook_id: Optional associated playbook ID.
        importance: Importance score (0.0 - 1.0).

    Returns:
        Memory ID if stored successfully, None otherwise.
    """
    memory_id = str(uuid4())
    now = datetime.utcnow()

    # Store in SQLite
    try:
        from memory.database import AgentMemoryRow, async_session_factory

        if async_session_factory is not None:
            async with async_session_factory() as session:
                row = AgentMemoryRow(
                    id=memory_id,
                    agent_role=agent_role,
                    content=content,
                    importance=importance,
                    playbook_id=playbook_id,
                    created_at=now,
                )
                session.add(row)
                await session.commit()
    except Exception as e:
        logger.error("Failed to store memory in database: %s", e)

    # Store in ChromaDB for vector search
    try:
        import httpx

        from config import settings

        chroma_url = settings.chroma_url.rstrip("/")

        async with httpx.AsyncClient(timeout=10) as client:
            # Ensure collection exists
            resp = await client.post(
                f"{chroma_url}/api/v1/collections",
                json={"name": _COLLECTION_NAME, "get_or_create": True},
            )

            collection_resp = await client.get(
                f"{chroma_url}/api/v1/collections/{_COLLECTION_NAME}",
            )
            if collection_resp.status_code != 200:
                logger.warning("Cannot access ChromaDB collection")
                return memory_id

            collection_data = collection_resp.json()
            collection_id = collection_data.get("id", "")

            # Add document
            await client.post(
                f"{chroma_url}/api/v1/collections/{collection_id}/add",
                json={
                    "ids": [memory_id],
                    "documents": [content],
                    "metadatas": [{
                        "agent_role": agent_role,
                        "playbook_id": playbook_id or "",
                        "importance": importance,
                        "created_at": now.isoformat(),
                    }],
                },
            )

        logger.debug("Memory stored: %s (role=%s)", memory_id[:8], agent_role)
        return memory_id

    except Exception as e:
        logger.debug("ChromaDB store failed (memory still in SQLite): %s", e)
        return memory_id


async def _fallback_recall(
    query: str,
    agent_role: Optional[str] = None,
    limit: int = 5,
) -> str:
    """
    Fallback memory recall using SQLite text search when ChromaDB is unavailable.

    Uses simple LIKE matching on content.
    """
    try:
        from sqlalchemy import select

        from memory.database import AgentMemoryRow, async_session_factory

        if async_session_factory is None:
            return ""

        async with async_session_factory() as session:
            stmt = select(AgentMemoryRow)

            if agent_role:
                stmt = stmt.where(AgentMemoryRow.agent_role == agent_role)

            # Simple text search (LIKE)
            keywords = query.split()[:3]  # First 3 words
            for keyword in keywords:
                if len(keyword) >= 3:
                    stmt = stmt.where(
                        AgentMemoryRow.content.contains(keyword)
                    )

            stmt = stmt.order_by(AgentMemoryRow.importance.desc()).limit(limit)
            result = await session.execute(stmt)
            rows = result.scalars().all()

            if not rows:
                return ""

            memories = []
            for i, row in enumerate(rows, 1):
                memories.append(f"[Memory {i}] ({row.agent_role}): {row.content[:300]}")

            return "\n".join(memories)

    except Exception as e:
        logger.debug("Fallback memory recall failed: %s", e)
        return ""
