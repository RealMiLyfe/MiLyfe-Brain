"""Runtime settings CRUD."""

from fastapi import APIRouter

from models.schemas import SettingsResponse, SettingsUpdate

router = APIRouter()


@router.get("/", response_model=SettingsResponse)
async def get_settings():
    """Get all runtime settings."""
    from memory.database import db

    rows = await db.fetch_all("SELECT key, value FROM settings")
    settings_dict = {row["key"]: row["value"] for row in rows}
    return SettingsResponse(settings=settings_dict)


@router.post("/", response_model=SettingsResponse)
async def save_settings(update: SettingsUpdate):
    """Save runtime settings."""
    from memory.database import db
    from datetime import datetime

    now = datetime.utcnow().isoformat()

    for key, value in update.settings.items():
        existing = await db.fetch_one("SELECT key FROM settings WHERE key = ?", (key,))
        if existing:
            await db.execute(
                "UPDATE settings SET value = ?, updated_at = ? WHERE key = ?",
                (str(value), now, key),
            )
        else:
            await db.execute(
                "INSERT INTO settings (key, value, updated_at) VALUES (?, ?, ?)",
                (key, str(value), now),
            )

    return await get_settings()
