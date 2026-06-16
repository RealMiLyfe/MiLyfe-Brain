"""Runtime Settings — DB-backed runtime configuration."""

from typing import Any, Optional

import structlog

logger = structlog.get_logger()


class RuntimeSettings:
    """Database-backed runtime settings that persist across restarts."""

    _cache: dict[str, str] = {}

    async def get(self, key: str, default: Any = None) -> Any:
        """Get a runtime setting."""
        if key in self._cache:
            return self._cache[key]

        from memory.database import db
        row = await db.fetch_one("SELECT value FROM settings WHERE key = ?", (key,))
        if row:
            self._cache[key] = row["value"]
            return row["value"]
        return default

    async def set(self, key: str, value: Any) -> None:
        """Set a runtime setting."""
        from memory.database import db
        from datetime import datetime

        str_value = str(value)
        now = datetime.utcnow().isoformat()

        existing = await db.fetch_one("SELECT key FROM settings WHERE key = ?", (key,))
        if existing:
            await db.execute("UPDATE settings SET value = ?, updated_at = ? WHERE key = ?", (str_value, now, key))
        else:
            await db.execute("INSERT INTO settings (key, value, updated_at) VALUES (?, ?, ?)", (key, str_value, now))

        self._cache[key] = str_value

    async def get_all(self) -> dict[str, str]:
        """Get all settings."""
        from memory.database import db
        rows = await db.fetch_all("SELECT key, value FROM settings")
        return {row["key"]: row["value"] for row in rows}

    def clear_cache(self) -> None:
        """Clear settings cache."""
        self._cache.clear()


# Global instance
runtime_settings = RuntimeSettings()
