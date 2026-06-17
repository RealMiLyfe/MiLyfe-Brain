"""
MiLyfe Brain - Database Layer

Async SQLAlchemy with SQLite WAL mode optimization.
Provides all ORM models, session management, and initialization.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import AsyncGenerator, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    Index,
    Integer,
    String,
    Text,
    event,
)
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from config import settings

logger = logging.getLogger(__name__)

# Module-level globals
engine = None
async_session_factory: Optional[async_sessionmaker[AsyncSession]] = None


# ============================================================
# SQLite Pragmas for WAL Mode Optimization
# ============================================================


def _set_sqlite_pragmas(dbapi_conn, connection_record) -> None:
    """Set SQLite performance pragmas on each new connection."""
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.execute("PRAGMA mmap_size=268435456")
    cursor.execute("PRAGMA cache_size=-65536")
    cursor.execute("PRAGMA temp_store=MEMORY")
    cursor.execute("PRAGMA busy_timeout=5000")
    cursor.close()


# ============================================================
# Base Model
# ============================================================


class Base(DeclarativeBase):
    """SQLAlchemy declarative base."""
    pass


# ============================================================
# ORM Models
# ============================================================


class PlaybookRow(Base):
    """Playbook records."""
    __tablename__ = "playbooks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    goal: Mapped[str] = mapped_column(Text, nullable=False)
    context: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="draft")
    priority: Mapped[int] = mapped_column(Integer, default=5)
    tags: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON array
    total_tokens: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    __table_args__ = (
        Index("ix_playbooks_status_created", "status", "created_at"),
    )


class PlaybookStepRow(Base):
    """Playbook step records."""
    __tablename__ = "playbook_steps"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    playbook_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    agent_role: Mapped[str] = mapped_column(String(50), default="orchestrator")
    status: Mapped[str] = mapped_column(String(50), default="pending")
    order_num: Mapped[int] = mapped_column(Integer, default=0)
    dependencies: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON array
    output: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    retries: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    __table_args__ = (
        Index("ix_steps_playbook_status", "playbook_id", "status"),
    )


class ActionLogRow(Base):
    """Action audit log records."""
    __tablename__ = "action_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    playbook_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    step_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    agent_role: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    action_type: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON
    risk_level: Mapped[str] = mapped_column(String(20), default="low")
    success: Mapped[bool] = mapped_column(Boolean, default=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_logs_playbook_time", "playbook_id", "timestamp"),
        Index("ix_logs_role_type", "agent_role", "action_type"),
    )


class ChatMessageRow(Base):
    """Chat message records."""
    __tablename__ = "chat_messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    session_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_chat_session_time", "session_id", "timestamp"),
    )


class ChatSessionRow(Base):
    """Chat session records."""
    __tablename__ = "chat_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    title: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    topic: Mapped[str] = mapped_column(String(50), default="general")
    message_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class AgentMemoryRow(Base):
    """Agent memory records."""
    __tablename__ = "agent_memories"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    agent_role: Mapped[str] = mapped_column(String(50), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    importance: Mapped[float] = mapped_column(Float, default=0.5)
    metadata_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON
    playbook_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    __table_args__ = (
        Index("ix_memories_role_importance", "agent_role", "importance"),
    )


class SkillRow(Base):
    """Skill definition records."""
    __tablename__ = "skills"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    trigger: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    steps: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON array
    agent_role: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    tags: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON array
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class SettingsRow(Base):
    """Runtime settings key-value store."""
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(200), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ScheduledJobRow(Base):
    """Scheduled job records."""
    __tablename__ = "scheduled_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    cron_expression: Mapped[str] = mapped_column(String(100), nullable=False)
    playbook_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    action: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    last_run: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    next_run: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class NotificationRow(Base):
    """Notification records."""
    __tablename__ = "notifications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    type: Mapped[str] = mapped_column(String(20), default="info")
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    read: Mapped[bool] = mapped_column(Boolean, default=False)
    playbook_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_notif_read_time", "read", "created_at"),
    )


class TokenUsageRow(Base):
    """Token usage tracking records."""
    __tablename__ = "token_usage"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0)
    playbook_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    agent_role: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_tokens_model_time", "model", "timestamp"),
    )


# ============================================================
# Database Lifecycle Functions
# ============================================================


async def init_database() -> None:
    """Initialize the database engine, session factory, and create tables.

    Falls back to in-memory SQLite if the configured database is unavailable.
    """
    global engine, async_session_factory

    database_url = settings.database_url

    try:
        # Ensure data directory exists for file-based SQLite
        if "sqlite" in database_url and ":memory:" not in database_url:
            import os
            db_path = database_url.split("///")[-1] if "///" in database_url else ""
            if db_path:
                os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)

        engine = create_async_engine(
            database_url,
            pool_size=5,
            max_overflow=10,
            echo=False,
        )

        # Register SQLite pragmas for file-based databases
        if "sqlite" in database_url:
            event.listen(engine.sync_engine, "connect", _set_sqlite_pragmas)

        async_session_factory = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

        # Create all tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        logger.info("Database initialized successfully: %s", database_url)

    except Exception as e:
        logger.warning(
            "Failed to initialize database at %s, falling back to in-memory: %s",
            database_url,
            str(e),
        )
        # Fallback to in-memory SQLite
        engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            echo=False,
        )
        event.listen(engine.sync_engine, "connect", _set_sqlite_pragmas)

        async_session_factory = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        logger.info("Database initialized with in-memory fallback")


async def close_database() -> None:
    """Close the database engine and release connections."""
    global engine, async_session_factory

    if engine is not None:
        await engine.dispose()
        engine = None
        async_session_factory = None
        logger.info("Database connection closed")


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that provides an async database session.

    Usage:
        @router.get("/items")
        async def get_items(session: AsyncSession = Depends(get_session)):
            ...
    """
    if async_session_factory is None:
        raise RuntimeError("Database not initialized. Call init_database() first.")

    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
