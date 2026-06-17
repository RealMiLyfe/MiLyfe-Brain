"""MiLyfe Brain — DB-Backed Runtime Configuration."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

import structlog
from sqlalchemy import select

logger = structlog.get_logger()


class RuntimeSettingsService:
    """Read/write runtime settings from database."""

    async def get(self, key: str, default: Any = None) -> Any:
        """Get a runtime setting."""
        from memory.database import SettingsRow, async_session_factory

        async with async_session_factory() as session:
            row = await session.get(SettingsRow, key)
            return row.value if row else default

    async def set(self, key: str, value: str):
        """Set a runtime setting."""
        from memory.database import SettingsRow, async_session_factory

        async with async_session_factory() as session:
            row = await session.get(SettingsRow, key)
            if row:
                row.value = value
                row.updated_at = datetime.utcnow()
            else:
                session.add(SettingsRow(key=key, value=value, updated_at=datetime.utcnow()))
            await session.commit()

    async def get_all(self) -> dict:
        """Get all settings."""
        from memory.database import SettingsRow, async_session_factory

        async with async_session_factory() as session:
            result = await session.execute(select(SettingsRow))
            return {r.key: r.value for r in result.scalars().all()}


# Singleton
runtime_settings = RuntimeSettingsService()
