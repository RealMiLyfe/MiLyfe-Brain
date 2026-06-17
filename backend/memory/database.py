"""SQLite Async Database — Tables, init, queries.

Uses aiosqlite for async operations with SQLite.
"""

import aiosqlite
import structlog

from config import settings

logger = structlog.get_logger()

# Extract path from sqlite URL
DB_PATH = settings.database_url.replace("sqlite:///", "")


class Database:
    """Async SQLite database wrapper."""

    def __init__(self):
        self._db: aiosqlite.Connection | None = None

    async def connect(self):
        """Connect to SQLite database."""
        self._db = await aiosqlite.connect(DB_PATH)
        self._db.row_factory = aiosqlite.Row
        await self._db.execute("PRAGMA journal_mode=WAL")
        await self._db.execute("PRAGMA foreign_keys=ON")

    async def close(self):
        """Close database connection."""
        if self._db:
            await self._db.close()

    async def execute(self, query: str, params: tuple = ()) -> None:
        """Execute a query (INSERT, UPDATE, DELETE)."""
        if not self._db:
            await self.connect()
        async with self._db.execute(query, params):
            await self._db.commit()

    async def fetch_one(self, query: str, params: tuple = ()) -> dict | None:
        """Fetch a single row."""
        if not self._db:
            await self.connect()
        async with self._db.execute(query, params) as cursor:
            row = await cursor.fetchone()
            if row:
                return dict(row)
            return None

    async def fetch_all(self, query: str, params: tuple = ()) -> list[dict]:
        """Fetch all rows."""
        if not self._db:
            await self.connect()
        async with self._db.execute(query, params) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


# Global instance
db = Database()


async def init_db():
    """Initialize database — create all tables."""
    await db.connect()

    # Create tables
    await db.execute("""
        CREATE TABLE IF NOT EXISTS playbooks (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            raw_text TEXT,
            status TEXT DEFAULT 'pending',
            created_at TEXT NOT NULL,
            completed_at TEXT,
            error TEXT
        )
    """)

    await db.execute("""
        CREATE TABLE IF NOT EXISTS playbook_steps (
            id TEXT PRIMARY KEY,
            playbook_id TEXT NOT NULL,
            description TEXT NOT NULL,
            agent_role TEXT,
            status TEXT DEFAULT 'pending',
            result TEXT,
            started_at TEXT,
            completed_at TEXT,
            FOREIGN KEY (playbook_id) REFERENCES playbooks(id)
        )
    """)

    await db.execute("""
        CREATE TABLE IF NOT EXISTS action_logs (
            id TEXT PRIMARY KEY,
            playbook_id TEXT,
            agent_id TEXT,
            agent_role TEXT,
            action_type TEXT NOT NULL,
            description TEXT NOT NULL,
            result TEXT,
            timestamp TEXT NOT NULL
        )
    """)

    await db.execute("""
        CREATE TABLE IF NOT EXISTS chat_messages (
            id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            model TEXT,
            tokens_used INTEGER DEFAULT 0,
            tool_calls TEXT DEFAULT '[]',
            attachments TEXT DEFAULT '[]',
            created_at TEXT NOT NULL
        )
    """)

    await db.execute("""
        CREATE TABLE IF NOT EXISTS agent_memories (
            id TEXT PRIMARY KEY,
            role TEXT NOT NULL,
            memory_type TEXT NOT NULL,
            content TEXT NOT NULL,
            importance REAL DEFAULT 0.5,
            recall_count INTEGER DEFAULT 0,
            created_at TEXT NOT NULL
        )
    """)

    await db.execute("""
        CREATE TABLE IF NOT EXISTS skills (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT NOT NULL,
            category TEXT NOT NULL,
            steps_json TEXT DEFAULT '[]',
            source_playbook_id TEXT,
            success_count INTEGER DEFAULT 0,
            created_at TEXT NOT NULL
        )
    """)

    await db.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)

    await db.execute("""
        CREATE TABLE IF NOT EXISTS scheduled_jobs (
            id TEXT PRIMARY KEY,
            playbook_id TEXT,
            title TEXT NOT NULL,
            cron_expression TEXT NOT NULL,
            enabled INTEGER DEFAULT 1,
            last_run TEXT,
            next_run TEXT,
            created_at TEXT NOT NULL
        )
    """)

    await db.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            type TEXT DEFAULT 'info',
            read INTEGER DEFAULT 0,
            created_at TEXT NOT NULL
        )
    """)

    await db.execute("""
        CREATE TABLE IF NOT EXISTS token_usage (
            id TEXT PRIMARY KEY,
            agent_id TEXT,
            agent_role TEXT,
            model TEXT,
            playbook_id TEXT,
            prompt_tokens INTEGER DEFAULT 0,
            completion_tokens INTEGER DEFAULT 0,
            timestamp TEXT NOT NULL
        )
    """)

    await db.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id TEXT PRIMARY KEY,
            filename TEXT NOT NULL,
            content_type TEXT NOT NULL,
            chunk_count INTEGER DEFAULT 0,
            created_at TEXT NOT NULL
        )
    """)

    # Create indexes
    await db.execute("CREATE INDEX IF NOT EXISTS idx_steps_playbook ON playbook_steps(playbook_id)")
    await db.execute("CREATE INDEX IF NOT EXISTS idx_logs_playbook ON action_logs(playbook_id)")
    await db.execute("CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON action_logs(timestamp)")
    await db.execute("CREATE INDEX IF NOT EXISTS idx_chat_session ON chat_messages(session_id)")
    await db.execute("CREATE INDEX IF NOT EXISTS idx_tokens_timestamp ON token_usage(timestamp)")

    logger.info("Database initialized", tables=10)
