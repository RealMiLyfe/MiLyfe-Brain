"""Memory Persistence — Long-term agent memory (SQLite)."""

import uuid
from datetime import datetime
from typing import Optional

import structlog

logger = structlog.get_logger()


class MemoryPersistence:
    """Long-term memory storage for agents."""

    async def store(
        self,
        role: str,
        content: str,
        memory_type: str = "observation",
        importance: float = 0.5,
    ) -> str:
        """Store a memory."""
        from memory.database import db

        memory_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()

        await db.execute(
            """INSERT INTO agent_memories (id, role, memory_type, content, importance, recall_count, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (memory_id, role, memory_type, content, importance, 0, now),
        )
        return memory_id

    async def recall(self, role: str, limit: int = 10) -> list[dict]:
        """Recall memories for a role, ordered by importance."""
        from memory.database import db

        rows = await db.fetch_all(
            "SELECT * FROM agent_memories WHERE role = ? ORDER BY importance DESC, created_at DESC LIMIT ?",
            (role, limit),
        )

        # Increment recall count
        for row in rows:
            await db.execute(
                "UPDATE agent_memories SET recall_count = recall_count + 1 WHERE id = ?",
                (row["id"],),
            )

        return [dict(r) for r in rows]

    async def forget(self, memory_id: str) -> None:
        """Delete a memory."""
        from memory.database import db
        await db.execute("DELETE FROM agent_memories WHERE id = ?", (memory_id,))


# Global instance
memory_persistence = MemoryPersistence()
