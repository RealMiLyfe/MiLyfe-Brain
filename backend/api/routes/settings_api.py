"""MiLyfe Brain — Runtime Settings Routes."""

from __future__ import annotations

from datetime import datetime

import orjson
from fastapi import APIRouter
from sqlalchemy import select

from memory.database import SettingsRow, async_session_factory
from models.schemas import RuntimeSettings

router = APIRouter()


@router.get("/", response_model=RuntimeSettings)
async def get_settings():
    """Load runtime settings."""
    async with async_session_factory() as session:
        result = await session.execute(select(SettingsRow))
        rows = {r.key: r.value for r in result.scalars().all()}

    return RuntimeSettings(
        light_model=rows.get("light_model", "phi3:mini"),
        heavy_model=rows.get("heavy_model", "llama3.1:8b"),
        premium_model=rows.get("premium_model", "llama3.1:70b"),
        require_approval_destructive=rows.get("require_approval_destructive", "true") == "true",
        require_approval_browsing=rows.get("require_approval_browsing", "true") == "true",
        require_approval_gui=rows.get("require_approval_gui", "true") == "true",
        auto_git_snapshots=rows.get("auto_git_snapshots", "true") == "true",
        output_style=rows.get("output_style", "default"),
        max_retries=int(rows.get("max_retries", "3")),
        context_summarize_threshold=int(rows.get("context_summarize_threshold", "32000")),
    )


@router.post("/", response_model=RuntimeSettings)
async def save_settings(data: RuntimeSettings):
    """Save runtime settings."""
    settings_dict = {
        "light_model": data.light_model,
        "heavy_model": data.heavy_model,
        "premium_model": data.premium_model,
        "require_approval_destructive": str(data.require_approval_destructive).lower(),
        "require_approval_browsing": str(data.require_approval_browsing).lower(),
        "require_approval_gui": str(data.require_approval_gui).lower(),
        "auto_git_snapshots": str(data.auto_git_snapshots).lower(),
        "output_style": data.output_style.value if hasattr(data.output_style, "value") else str(data.output_style),
        "max_retries": str(data.max_retries),
        "context_summarize_threshold": str(data.context_summarize_threshold),
    }

    async with async_session_factory() as session:
        for key, value in settings_dict.items():
            existing = await session.get(SettingsRow, key)
            if existing:
                existing.value = value
                existing.updated_at = datetime.utcnow()
            else:
                session.add(SettingsRow(key=key, value=value, updated_at=datetime.utcnow()))
        await session.commit()

    return data
