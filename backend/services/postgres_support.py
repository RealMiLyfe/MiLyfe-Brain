"""
PostgreSQL support for MiLyfe Brain (Phase 3 scale).

Provides a database abstraction that supports both SQLite (local) and
PostgreSQL (enterprise). Automatically selects backend based on DATABASE_URL.

Configuration:
    DATABASE_URL=sqlite:////data/milyfe.db           # SQLite (default)
    DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/milyfe  # PostgreSQL

Features when using PostgreSQL:
    - Connection pooling (asyncpg)
    - Full ACID transactions
    - Concurrent write support (no single-writer limitation)
    - JSONB columns for flexible data
    - Full-text search
    - Row-level security (future)
"""

import os
from typing import Optional

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool, QueuePool

from .logging_config import get_logger

logger = get_logger("database")


class DatabaseConfig:
    """Database configuration and engine factory."""

    def __init__(self, database_url: Optional[str] = None):
        self.database_url = database_url or os.getenv(
            "DATABASE_URL", "sqlite+aiosqlite:////data/milyfe.db"
        )
        self._engine = None
        self._session_factory = None

    @property
    def is_postgres(self) -> bool:
        """Check if using PostgreSQL."""
        return "postgresql" in self.database_url

    @property
    def is_sqlite(self) -> bool:
        """Check if using SQLite."""
        return "sqlite" in self.database_url

    def get_engine_kwargs(self) -> dict:
        """Get engine creation kwargs based on database type."""
        if self.is_postgres:
            return {
                "pool_size": int(os.getenv("DB_POOL_SIZE", "20")),
                "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", "10")),
                "pool_timeout": int(os.getenv("DB_POOL_TIMEOUT", "30")),
                "pool_recycle": int(os.getenv("DB_POOL_RECYCLE", "3600")),
                "pool_pre_ping": True,
                "poolclass": QueuePool,
                "echo": os.getenv("DB_ECHO", "false").lower() == "true",
            }
        else:
            # SQLite settings
            return {
                "poolclass": NullPool,  # SQLite doesn't support connection pooling well
                "echo": os.getenv("DB_ECHO", "false").lower() == "true",
            }

    def create_engine(self):
        """Create the async database engine."""
        url = self.database_url

        # Ensure async driver
        if url.startswith("sqlite:///") and "aiosqlite" not in url:
            url = url.replace("sqlite:///", "sqlite+aiosqlite:///")
        elif url.startswith("postgresql://") and "asyncpg" not in url:
            url = url.replace("postgresql://", "postgresql+asyncpg://")

        self._engine = create_async_engine(url, **self.get_engine_kwargs())

        # SQLite-specific configuration
        if self.is_sqlite:
            @event.listens_for(self._engine.sync_engine, "connect")
            def set_sqlite_pragma(dbapi_conn, connection_record):
                cursor = dbapi_conn.cursor()
                cursor.execute("PRAGMA journal_mode=WAL")
                cursor.execute("PRAGMA synchronous=NORMAL")
                cursor.execute("PRAGMA busy_timeout=5000")
                cursor.execute("PRAGMA cache_size=-64000")  # 64MB cache
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.close()

        # PostgreSQL-specific logging
        if self.is_postgres:
            logger.info(
                "PostgreSQL engine created",
                extra={
                    "pool_size": self.get_engine_kwargs().get("pool_size"),
                    "max_overflow": self.get_engine_kwargs().get("max_overflow"),
                },
            )
        else:
            logger.info("SQLite engine created")

        return self._engine

    def create_session_factory(self) -> async_sessionmaker:
        """Create the async session factory."""
        if not self._engine:
            self.create_engine()

        self._session_factory = async_sessionmaker(
            self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        return self._session_factory

    async def get_session(self) -> AsyncSession:
        """Get a database session."""
        if not self._session_factory:
            self.create_session_factory()
        async with self._session_factory() as session:
            yield session

    async def health_check(self) -> dict:
        """Check database connectivity."""
        try:
            if not self._engine:
                self.create_engine()

            async with self._engine.begin() as conn:
                if self.is_postgres:
                    result = await conn.execute("SELECT 1")
                else:
                    from sqlalchemy import text
                    result = await conn.execute(text("SELECT 1"))

            return {
                "status": "connected",
                "type": "postgresql" if self.is_postgres else "sqlite",
                "pool_size": self._engine.pool.size() if self.is_postgres else None,
            }
        except Exception as e:
            return {
                "status": "disconnected",
                "error": str(e),
            }

    async def close(self):
        """Close the engine and all connections."""
        if self._engine:
            await self._engine.dispose()
            logger.info("Database engine closed")


# Singleton instance
db_config = DatabaseConfig()
