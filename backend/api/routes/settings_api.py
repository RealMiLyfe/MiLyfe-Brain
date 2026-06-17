"""Settings API — Runtime configuration management."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services.runtime_settings import runtime_settings
from config import settings as app_settings

router = APIRouter()


class SettingUpdate(BaseModel):
    """Request body for updating a setting."""
    key: str
    value: str


@router.get("/")
async def get_settings() -> dict:
    """Get all runtime settings merged with app defaults."""
    db_settings = await runtime_settings.get_all()

    # Merge with relevant app settings
    defaults = {
        "default_light_model": app_settings.default_light_model,
        "default_heavy_model": app_settings.default_heavy_model,
        "premium_model": app_settings.premium_model,
        "max_agents": str(app_settings.max_agents),
        "agent_timeout": str(app_settings.agent_timeout),
        "require_approval_destructive": str(app_settings.require_approval_destructive),
        "require_approval_browsing": str(app_settings.require_approval_browsing),
        "auto_git_snapshots": str(app_settings.auto_git_snapshots),
        "workspace_dir": app_settings.workspace_dir,
    }

    # DB settings override defaults
    merged = {**defaults, **db_settings}
    return {"settings": merged}


@router.post("/")
async def update_settings(body: SettingUpdate) -> dict:
    """Update a single runtime setting."""
    if not body.key or not body.value:
        raise HTTPException(status_code=400, detail="Key and value are required")

    await runtime_settings.set(body.key, body.value)

    return {"message": "Setting updated", "key": body.key, "value": body.value}
