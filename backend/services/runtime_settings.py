"""Runtime Settings — Database-backed key-value configuration.

Provides get/set/get_all for persistent settings stored in the DB.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Dict, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from memory.database import async_session_factory, SettingModel

logger = logging.getLogger(__name__)


class RuntimeSettings:
    """Database-backed key-value settings store.

    Provides runtime-configurable settings that persist across restarts.
    Settings are stored in the 'settings' table.
    """

    async def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get a setting value by key.

        Args:
            key: The setting key.
            default: Default value if key not found.

        Returns:
            The setting value, or default if not found.
        """
        async with async_session_factory() as db:
            result = await db.execute(
                select(SettingModel).where(SettingModel.key == key)
            )
            row = result.scalar_one_or_none()
            return row.value if row else default

    async def set(self, key: str, value: str) -> None:
        """Set a setting value (create or update).

        Args:
            key: The setting key.
            value: The value to store.
        """
        async with async_session_factory() as db:
            result = await db.execute(
                select(SettingModel).where(SettingModel.key == key)
            )
            existing = result.scalar_one_or_none()

            if existing:
                existing.value = value
                existing.updated_at = datetime.utcnow()
            else:
                db.add(SettingModel(
                    key=key,
                    value=value,
                    updated_at=datetime.utcnow(),
                ))

            await db.commit()

    async def get_all(self) -> Dict[str, str]:
        """Get all settings as a dictionary.

        Returns:
            Dict of key -> value for all stored settings.
        """
        async with async_session_factory() as db:
            result = await db.execute(select(SettingModel))
            rows = result.scalars().all()

        return {row.key: row.value for row in rows}


# Singleton
runtime_settings = RuntimeSettings()
