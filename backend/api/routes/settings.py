"""
MiLyfe Brain - Settings Route

Runtime settings management (get/update).
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Dict

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from memory.database import SettingsRow, async_session_factory
from models.schemas import RuntimeSettings

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/", response_model=RuntimeSettings)
async def get_settings() -> RuntimeSettings:
    """Get current runtime settings."""
    from config import settings as app_settings

    # Start with defaults from config
    result = RuntimeSettings(
        default_light_model=app_settings.default_light_model,
        default_heavy_model=app_settings.default_heavy_model,
        premium_model=app_settings.premium_model,
        max_agents=app_settings.max_agents,
        agent_timeout=app_settings.agent_timeout,
        require_approval_destructive=app_settings.require_approval_destructive,
        require_approval_browsing=app_settings.require_approval_browsing,
        require_approval_gui=app_settings.require_approval_gui,
        auto_git_snapshots=app_settings.auto_git_snapshots,
        context_summarize_threshold=app_settings.context_summarize_threshold,
    )

    # Override with any database-stored runtime overrides
    if async_session_factory is not None:
        try:
            async with async_session_factory() as db:
                rows_result = await db.execute(select(SettingsRow))
                rows = rows_result.scalars().all()

            overrides: Dict[str, str] = {row.key: row.value for row in rows}

            for field_name in result.model_fields:
                if field_name in overrides:
                    value = overrides[field_name]
                    field_info = result.model_fields[field_name]
                    # Type-cast based on annotation
                    if "bool" in str(field_info.annotation):
                        setattr(result, field_name, value.lower() in ("true", "1", "yes"))
                    elif "int" in str(field_info.annotation):
                        setattr(result, field_name, int(value))
                    else:
                        setattr(result, field_name, value)
        except Exception as e:
            logger.warning("Failed to load runtime settings overrides: %s", e)

    return result


@router.put("/", response_model=RuntimeSettings)
async def update_settings(body: RuntimeSettings) -> RuntimeSettings:
    """Update runtime settings. Only non-None fields are updated."""
    if async_session_factory is None:
        raise HTTPException(status_code=503, detail="Database not available")

    now = datetime.utcnow()
    updates = body.model_dump(exclude_none=True)

    if not updates:
        raise HTTPException(status_code=400, detail="No settings to update")

    async with async_session_factory() as db:
        for key, value in updates.items():
            # Upsert setting
            result = await db.execute(
                select(SettingsRow).where(SettingsRow.key == key)
            )
            existing = result.scalar_one_or_none()

            str_value = str(value)

            if existing is not None:
                existing.value = str_value
                existing.updated_at = now
            else:
                row = SettingsRow(key=key, value=str_value, updated_at=now)
                db.add(row)

        await db.commit()

    logger.info("Updated %d runtime settings", len(updates))
    return await get_settings()
