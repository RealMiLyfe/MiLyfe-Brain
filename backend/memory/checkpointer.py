"""MiLyfe Brain — State Checkpointing.

Provides save/load/list checkpoint operations for playbook execution state.
Checkpoints are stored in the database for durability and enable
resume-from-failure semantics.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

import structlog
from sqlalchemy import Column, DateTime, Integer, String, Text, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from memory.database import Base, async_session_factory

logger = structlog.get_logger("checkpointer")


# ═══════════════════════════════════════════════════════════════════════
# CHECKPOINT ORM MODEL
# ═══════════════════════════════════════════════════════════════════════


class CheckpointModel(Base):
    """Checkpoints table — stores serialized playbook execution state."""

    __tablename__ = "checkpoints"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    playbook_id = Column(String(36), nullable=False, index=True)
    version = Column(Integer, nullable=False, default=1)
    state_json = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, default=func.now())


# ═══════════════════════════════════════════════════════════════════════
# CHECKPOINTER SERVICE
# ═══════════════════════════════════════════════════════════════════════


class Checkpointer:
    """Manages state checkpoints for playbook execution.

    Enables:
    - Saving intermediate execution state
    - Resuming from the last successful checkpoint
    - Listing all checkpoints for audit/debugging
    """

    async def save_checkpoint(
        self,
        playbook_id: str,
        state: Dict[str, Any],
        session: Optional[AsyncSession] = None,
    ) -> str:
        """Save a state checkpoint for a playbook.

        Args:
            playbook_id: The playbook this checkpoint belongs to.
            state: Arbitrary state dict to serialize and persist.
            session: Optional existing database session.

        Returns:
            The checkpoint ID.
        """
        checkpoint_id = str(uuid.uuid4())

        async def _save(db: AsyncSession) -> str:
            # Determine next version number
            result = await db.execute(
                select(func.max(CheckpointModel.version)).where(
                    CheckpointModel.playbook_id == playbook_id
                )
            )
            max_version = result.scalar() or 0
            next_version = max_version + 1

            checkpoint = CheckpointModel(
                id=checkpoint_id,
                playbook_id=playbook_id,
                version=next_version,
                state_json=json.dumps(state, default=str),
                created_at=datetime.utcnow(),
            )
            db.add(checkpoint)
            await db.flush()

            logger.info(
                "checkpoint_saved",
                playbook_id=playbook_id,
                checkpoint_id=checkpoint_id,
                version=next_version,
            )
            return checkpoint_id

        if session:
            return await _save(session)
        else:
            async with async_session_factory() as db:
                result = await _save(db)
                await db.commit()
                return result

    async def load_checkpoint(
        self,
        playbook_id: str,
        version: Optional[int] = None,
        session: Optional[AsyncSession] = None,
    ) -> Optional[Dict[str, Any]]:
        """Load the latest (or specified) checkpoint for a playbook.

        Args:
            playbook_id: The playbook to load checkpoint for.
            version: Specific version to load. If None, loads latest.
            session: Optional existing database session.

        Returns:
            Deserialized state dict, or None if no checkpoint exists.
        """

        async def _load(db: AsyncSession) -> Optional[Dict[str, Any]]:
            if version is not None:
                stmt = select(CheckpointModel).where(
                    CheckpointModel.playbook_id == playbook_id,
                    CheckpointModel.version == version,
                )
            else:
                stmt = (
                    select(CheckpointModel)
                    .where(CheckpointModel.playbook_id == playbook_id)
                    .order_by(CheckpointModel.version.desc())
                    .limit(1)
                )

            result = await db.execute(stmt)
            checkpoint = result.scalar_one_or_none()

            if checkpoint is None:
                logger.debug(
                    "checkpoint_not_found",
                    playbook_id=playbook_id,
                    version=version,
                )
                return None

            try:
                state = json.loads(checkpoint.state_json)
            except json.JSONDecodeError as exc:
                logger.error(
                    "checkpoint_deserialize_failed",
                    playbook_id=playbook_id,
                    checkpoint_id=checkpoint.id,
                    error=str(exc),
                )
                return None

            logger.debug(
                "checkpoint_loaded",
                playbook_id=playbook_id,
                checkpoint_id=checkpoint.id,
                version=checkpoint.version,
            )
            return state

        if session:
            return await _load(session)
        else:
            async with async_session_factory() as db:
                return await _load(db)

    async def list_checkpoints(
        self,
        playbook_id: str,
        session: Optional[AsyncSession] = None,
    ) -> List[Dict[str, Any]]:
        """List all checkpoints for a playbook (metadata only, no state).

        Args:
            playbook_id: The playbook to list checkpoints for.
            session: Optional existing database session.

        Returns:
            List of checkpoint metadata dicts sorted by version ascending.
        """

        async def _list(db: AsyncSession) -> List[Dict[str, Any]]:
            stmt = (
                select(CheckpointModel)
                .where(CheckpointModel.playbook_id == playbook_id)
                .order_by(CheckpointModel.version.asc())
            )
            result = await db.execute(stmt)
            checkpoints = result.scalars().all()

            return [
                {
                    "id": cp.id,
                    "playbook_id": cp.playbook_id,
                    "version": cp.version,
                    "created_at": cp.created_at.isoformat() if cp.created_at else None,
                }
                for cp in checkpoints
            ]

        if session:
            return await _list(session)
        else:
            async with async_session_factory() as db:
                return await _list(db)

    async def delete_checkpoints(
        self,
        playbook_id: str,
        keep_latest: int = 0,
        session: Optional[AsyncSession] = None,
    ) -> int:
        """Delete checkpoints for a playbook, optionally keeping the N most recent.

        Args:
            playbook_id: The playbook whose checkpoints to prune.
            keep_latest: Number of most recent checkpoints to keep.
            session: Optional existing database session.

        Returns:
            Number of checkpoints deleted.
        """
        from sqlalchemy import delete as sql_delete

        async def _delete(db: AsyncSession) -> int:
            if keep_latest > 0:
                # Find the version cutoff
                stmt = (
                    select(CheckpointModel.version)
                    .where(CheckpointModel.playbook_id == playbook_id)
                    .order_by(CheckpointModel.version.desc())
                    .offset(keep_latest)
                    .limit(1)
                )
                result = await db.execute(stmt)
                cutoff_version = result.scalar_one_or_none()

                if cutoff_version is None:
                    # Fewer checkpoints than keep_latest — nothing to delete
                    return 0

                del_stmt = sql_delete(CheckpointModel).where(
                    CheckpointModel.playbook_id == playbook_id,
                    CheckpointModel.version <= cutoff_version,
                )
            else:
                del_stmt = sql_delete(CheckpointModel).where(
                    CheckpointModel.playbook_id == playbook_id
                )

            result = await db.execute(del_stmt)
            deleted = result.rowcount
            logger.info(
                "checkpoints_deleted",
                playbook_id=playbook_id,
                deleted=deleted,
                kept=keep_latest,
            )
            return deleted

        if session:
            return await _delete(session)
        else:
            async with async_session_factory() as db:
                count = await _delete(db)
                await db.commit()
                return count


# ═══════════════════════════════════════════════════════════════════════
# MODULE-LEVEL SINGLETON
# ═══════════════════════════════════════════════════════════════════════

checkpointer = Checkpointer()
