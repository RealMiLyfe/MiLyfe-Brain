"""MiLyfe Brain — Async SQLAlchemy Database Layer.

Uses aiosqlite for local-first SQLite with async/await support.
All ORM models mirror the Alembic migration schema.
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import AsyncGenerator

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, relationship

from config import settings

# ═══════════════════════════════════════════════════════════════════════
# ENGINE & SESSION
# ═══════════════════════════════════════════════════════════════════════

# Ensure database directory exists
_db_path = settings.database_url.replace("sqlite+aiosqlite:///", "")
_db_dir = os.path.dirname(_db_path)
if _db_dir:
    os.makedirs(_db_dir, exist_ok=True)

engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    future=True,
    connect_args={"check_same_thread": False},
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# ═══════════════════════════════════════════════════════════════════════
# BASE
# ═══════════════════════════════════════════════════════════════════════


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""

    pass


# ═══════════════════════════════════════════════════════════════════════
# ORM MODELS
# ═══════════════════════════════════════════════════════════════════════


class PlaybookModel(Base):
    """Playbooks table — top-level execution plans."""

    __tablename__ = "playbooks"

    id = Column(String(36), primary_key=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=False, default="")
    raw_text = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default="pending")
    created_at = Column(DateTime, nullable=False, default=func.now())
    completed_at = Column(DateTime, nullable=True)
    error = Column(Text, nullable=True)

    # Relationships
    steps = relationship(
        "PlaybookStepModel",
        back_populates="playbook",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class PlaybookStepModel(Base):
    """Playbook steps table — individual execution steps."""

    __tablename__ = "playbook_steps"

    id = Column(String(36), primary_key=True)
    playbook_id = Column(
        String(36),
        ForeignKey("playbooks.id", ondelete="CASCADE"),
        nullable=False,
    )
    description = Column(Text, nullable=False)
    agent_role = Column(String(20), nullable=True)
    status = Column(String(20), nullable=False, default="pending")
    result = Column(Text, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    order_index = Column(Integer, nullable=False, default=0)
    depends_on = Column(Text, nullable=True)  # JSON array of step IDs
    complexity = Column(String(10), nullable=True, default="medium")

    # Relationships
    playbook = relationship("PlaybookModel", back_populates="steps")


class ActionLogModel(Base):
    """Action logs table — audit trail of all agent actions."""

    __tablename__ = "action_logs"

    id = Column(String(36), primary_key=True)
    playbook_id = Column(
        String(36),
        ForeignKey("playbooks.id", ondelete="SET NULL"),
        nullable=True,
    )
    agent_id = Column(String(36), nullable=True)
    agent_role = Column(String(20), nullable=True)
    action_type = Column(String(30), nullable=False)
    description = Column(Text, nullable=False)
    result = Column(Text, nullable=True)
    timestamp = Column(DateTime, nullable=False, default=func.now())


class ChatMessageModel(Base):
    """Chat messages table — conversation history."""

    __tablename__ = "chat_messages"

    id = Column(String(36), primary_key=True)
    session_id = Column(String(36), nullable=False, index=True)
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    model = Column(String(100), nullable=True)
    tokens_used = Column(Integer, nullable=True, default=0)
    tool_calls = Column(Text, nullable=True)  # JSON
    attachments = Column(Text, nullable=True)  # JSON
    created_at = Column(DateTime, nullable=False, default=func.now())


class AgentMemoryModel(Base):
    """Agent memories table — persistent memory for agents."""

    __tablename__ = "agent_memories"

    id = Column(String(36), primary_key=True)
    role = Column(String(20), nullable=False, index=True)
    memory_type = Column(String(30), nullable=False)
    content = Column(Text, nullable=False)
    importance = Column(Float, nullable=False, default=0.5)
    recall_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=func.now())


class SkillModel(Base):
    """Skills table — learned reusable patterns."""

    __tablename__ = "skills"

    id = Column(String(36), primary_key=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    category = Column(String(50), nullable=True)
    steps_json = Column(Text, nullable=False)
    source_playbook_id = Column(String(36), nullable=True)
    success_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=func.now())


class SettingModel(Base):
    """Settings table — key-value configuration persistence."""

    __tablename__ = "settings"

    key = Column(String(100), primary_key=True)
    value = Column(Text, nullable=False)
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())


class ScheduledJobModel(Base):
    """Scheduled jobs table — cron-based recurring tasks."""

    __tablename__ = "scheduled_jobs"

    id = Column(String(36), primary_key=True)
    playbook_id = Column(String(36), nullable=True)
    title = Column(String(200), nullable=False)
    cron_expression = Column(String(100), nullable=False)
    enabled = Column(Boolean, nullable=False, default=True)
    last_run = Column(DateTime, nullable=True)
    next_run = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=func.now())


class NotificationDBModel(Base):
    """Notifications table — user-facing alerts."""

    __tablename__ = "notifications"

    id = Column(String(36), primary_key=True)
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    type = Column(String(30), nullable=False, default="info")
    read = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=func.now())


class TokenUsageModel(Base):
    """Token usage table — LLM consumption tracking."""

    __tablename__ = "token_usage"

    id = Column(String(36), primary_key=True)
    agent_id = Column(String(36), nullable=True)
    agent_role = Column(String(20), nullable=True)
    model = Column(String(100), nullable=False)
    playbook_id = Column(String(36), nullable=True)
    prompt_tokens = Column(Integer, nullable=False, default=0)
    completion_tokens = Column(Integer, nullable=False, default=0)
    timestamp = Column(DateTime, nullable=False, default=func.now())


# ═══════════════════════════════════════════════════════════════════════
# DATABASE INITIALIZATION
# ═══════════════════════════════════════════════════════════════════════


async def init_db() -> None:
    """Create all tables if they don't exist.

    This is safe to call multiple times — SQLAlchemy's
    create_all uses IF NOT EXISTS semantics.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


# ═══════════════════════════════════════════════════════════════════════
# DEPENDENCY INJECTION
# ═══════════════════════════════════════════════════════════════════════


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields an async database session.

    Usage:
        @router.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
