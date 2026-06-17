"""MiLyfe Brain — SQLite Database (Optimized Async SQLAlchemy).

Optimizations:
- WAL mode for concurrent read/write
- Connection pooling with proper sizing
- Proper indexes on hot columns
- Graceful degradation on failures
- Auto-vacuum and pragma tuning
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

import structlog
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    Index,
    Integer,
    String,
    Text,
    event,
    text,
)
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.pool import StaticPool

from config import settings

logger = structlog.get_logger()

# ============================================================
# Engine & Session (Optimized)
# ============================================================

engine = create_async_engine(
    settings.database_url,
    echo=False,
    pool_pre_ping=True,
    # For SQLite: use StaticPool with single connection for writes,
    # but allow concurrent reads via WAL mode
    connect_args={
        "check_same_thread": False,
        "timeout": 30,
    },
    # Pool configuration
    pool_size=5,
    max_overflow=10,
    pool_recycle=3600,
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_session() -> AsyncSession:
    """Dependency for FastAPI routes."""
    async with async_session_factory() as session:
        yield session


# ============================================================
# SQLite Pragmas (Performance Tuning)
# ============================================================


@event.listens_for(engine.sync_engine, "connect")
def _set_sqlite_pragmas(dbapi_connection, connection_record):
    """Set SQLite performance pragmas on every new connection."""
    cursor = dbapi_connection.cursor()
    # WAL mode: allows concurrent reads during writes
    cursor.execute("PRAGMA journal_mode=WAL")
    # Synchronous NORMAL: good balance of safety and speed
    cursor.execute("PRAGMA synchronous=NORMAL")
    # Memory-mapped I/O: faster reads (256MB)
    cursor.execute("PRAGMA mmap_size=268435456")
    # Cache size: 64MB (negative = KB)
    cursor.execute("PRAGMA cache_size=-65536")
    # Temp store in memory
    cursor.execute("PRAGMA temp_store=MEMORY")
    # Busy timeout: wait up to 5s for locks
    cursor.execute("PRAGMA busy_timeout=5000")
    # Auto-vacuum: incremental (doesn't block)
    cursor.execute("PRAGMA auto_vacuum=INCREMENTAL")
    # Page size: 4096 (optimal for modern SSDs)
    cursor.execute("PRAGMA page_size=4096")
    cursor.close()


# ============================================================
# Base Model
# ============================================================


class Base(DeclarativeBase):
    pass


# ============================================================
# Tables (with optimized indexes)
# ============================================================


class PlaybookRow(Base):
    __tablename__ = "playbooks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    raw_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="queued", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    model_override: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    tags: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0)

    __table_args__ = (
        Index("ix_playbooks_status_created", "status", "created_at"),
    )


class PlaybookStepRow(Base):
    __tablename__ = "playbook_steps"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    playbook_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    agent_role: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    result: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    depends_on: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    complexity: Mapped[str] = mapped_column(String(10), default="medium")
    tools_needed: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    order_index: Mapped[int] = mapped_column(Integer, default=0)

    __table_args__ = (
        Index("ix_steps_playbook_status", "playbook_id", "status"),
        Index("ix_steps_playbook_order", "playbook_id", "order_index"),
    )


class ActionLogRow(Base):
    __tablename__ = "action_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    playbook_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    agent_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    agent_role: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, index=True)
    action_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    result: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    risk_level: Mapped[str] = mapped_column(String(15), default="safe")
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    __table_args__ = (
        Index("ix_logs_playbook_time", "playbook_id", "timestamp"),
        Index("ix_logs_role_type", "agent_role", "action_type"),
        Index("ix_logs_risk_time", "risk_level", "timestamp"),
    )


class ChatMessageRow(Base):
    __tablename__ = "chat_messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    session_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(15), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    tokens_used: Mapped[int] = mapped_column(Integer, default=0)
    tool_calls: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    attachments: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_chat_session_time", "session_id", "created_at"),
    )


class AgentMemoryRow(Base):
    __tablename__ = "agent_memories"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    role: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    memory_type: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    importance: Mapped[float] = mapped_column(Float, default=0.5)
    recall_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_memories_role_importance", "role", "importance"),
    )


class SkillRow(Base):
    __tablename__ = "skills"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    steps_json: Mapped[str] = mapped_column(Text, nullable=False)
    source_playbook_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    success_count: Mapped[int] = mapped_column(Integer, default=0)
    triggers: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class SettingsRow(Base):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ScheduledJobRow(Base):
    __tablename__ = "scheduled_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    playbook_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    cron_expression: Mapped[str] = mapped_column(String(100), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    last_run: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    next_run: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class NotificationRow(Base):
    __tablename__ = "notifications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[str] = mapped_column(String(15), default="info")
    read: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    data: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    __table_args__ = (
        Index("ix_notif_read_time", "read", "created_at"),
    )


class TokenUsageRow(Base):
    __tablename__ = "token_usage"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    agent_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    agent_role: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, index=True)
    model: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    playbook_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    __table_args__ = (
        Index("ix_tokens_model_time", "model", "timestamp"),
        Index("ix_tokens_role_time", "agent_role", "timestamp"),
    )


class ChatSessionRow(Base):
    __tablename__ = "chat_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    title: Mapped[str] = mapped_column(String(200), default="New Chat")
    message_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


# ============================================================
# Database Initialization (with graceful degradation)
# ============================================================


async def init_database():
    """Create all tables if they don't exist. Gracefully handles failures."""
    global engine, async_session_factory

    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        # Run PRAGMA incremental_vacuum after init
        async with async_session_factory() as session:
            await session.execute(text("PRAGMA incremental_vacuum(100)"))
            await session.commit()

        logger.info("database_initialized", tables=len(Base.metadata.tables))

    except Exception as e:
        logger.error("database_init_failed", error=str(e))
        # Try fallback: in-memory database
        logger.warning("attempting_memory_fallback")
        try:
            from sqlalchemy.ext.asyncio import create_async_engine as create_fallback
            engine = create_fallback(
                "sqlite+aiosqlite:///:memory:",
                echo=False,
                connect_args={"check_same_thread": False},
            )
            async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.warning("database_fallback_memory", note="Using in-memory DB — data will not persist")
        except Exception as e2:
            logger.critical("database_completely_failed", error=str(e2))
            raise


async def close_database():
    """Dispose of the engine gracefully."""
    try:
        # Run checkpoint before closing (ensure WAL is flushed)
        async with async_session_factory() as session:
            await session.execute(text("PRAGMA wal_checkpoint(TRUNCATE)"))
            await session.commit()
    except Exception:
        pass
    await engine.dispose()


async def vacuum_database():
    """Run incremental vacuum to reclaim space."""
    try:
        async with async_session_factory() as session:
            await session.execute(text("PRAGMA incremental_vacuum(500)"))
            await session.commit()
        logger.debug("database_vacuumed")
    except Exception as e:
        logger.warning("vacuum_failed", error=str(e))


async def get_database_stats() -> dict:
    """Get database size and performance stats."""
    try:
        async with async_session_factory() as session:
            result = await session.execute(text("PRAGMA page_count"))
            page_count = result.scalar() or 0
            result2 = await session.execute(text("PRAGMA page_size"))
            page_size = result2.scalar() or 4096
            result3 = await session.execute(text("PRAGMA journal_mode"))
            journal = result3.scalar() or "unknown"

            # Table counts
            tables = {}
            for table_name in ["playbooks", "playbook_steps", "action_logs", "chat_messages", "token_usage", "notifications"]:
                try:
                    r = await session.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                    tables[table_name] = r.scalar() or 0
                except Exception:
                    tables[table_name] = -1

        return {
            "size_bytes": page_count * page_size,
            "size_mb": round((page_count * page_size) / (1024 * 1024), 2),
            "page_count": page_count,
            "page_size": page_size,
            "journal_mode": journal,
            "table_counts": tables,
        }
    except Exception as e:
        return {"error": str(e)}
