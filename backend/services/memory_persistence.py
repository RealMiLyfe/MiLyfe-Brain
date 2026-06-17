"""MiLyfe Brain — Long-Term Memory Persistence (SQLite)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Dict, List, Optional

import structlog
from sqlalchemy import select, update

from models.schemas import AgentMemory, AgentRole

logger = structlog.get_logger()


class MemoryPersistence:
    """Manages long-term agent memories in SQLite."""

    async def store(
        self,
        role: AgentRole,
        content: str,
        memory_type: str = "fact",
        importance: float = 0.5,
    ) -> str:
        """Store a new memory."""
        from memory.database import AgentMemoryRow, async_session_factory

        memory_id = str(uuid.uuid4())
        async with async_session_factory() as session:
            session.add(AgentMemoryRow(
                id=memory_id,
                role=role.value,
                memory_type=memory_type,
                content=content[:5000],
                importance=importance,
                recall_count=0,
                created_at=datetime.utcnow(),
            ))
            await session.commit()

        return memory_id

    async def recall(
        self,
        role: Optional[AgentRole] = None,
        memory_type: Optional[str] = None,
        limit: int = 20,
    ) -> List[AgentMemory]:
        """Recall memories, optionally filtered."""
        from memory.database import AgentMemoryRow, async_session_factory

        async with async_session_factory() as session:
            query = select(AgentMemoryRow).order_by(
                AgentMemoryRow.importance.desc(),
                AgentMemoryRow.recall_count.desc(),
            )
            if role:
                query = query.where(AgentMemoryRow.role == role.value)
            if memory_type:
                query = query.where(AgentMemoryRow.memory_type == memory_type)
            query = query.limit(limit)

            result = await session.execute(query)
            rows = result.scalars().all()

            # Increment recall counts
            for row in rows:
                row.recall_count += 1
            await session.commit()

            return [
                AgentMemory(
                    id=r.id,
                    role=r.role,
                    memory_type=r.memory_type,
                    content=r.content,
                    importance=r.importance,
                    recall_count=r.recall_count,
                    created_at=r.created_at,
                )
                for r in rows
            ]

    async def forget(self, memory_id: str):
        """Delete a memory."""
        from memory.database import AgentMemoryRow, async_session_factory

        async with async_session_factory() as session:
            row = await session.get(AgentMemoryRow, memory_id)
            if row:
                await session.delete(row)
                await session.commit()


# Singleton
memory_persistence = MemoryPersistence()
