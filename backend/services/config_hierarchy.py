"""MiLyfe Brain — Multi-Layer Configuration Cascade."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

import yaml
import structlog

from config import settings

logger = structlog.get_logger()


class ConfigHierarchy:
    """4-layer config: system → user → workspace → subdirectory.

    Dot-notation access: config.get("models.heavy")
    Later layers override earlier ones (deep merge).
    """

    def __init__(self):
        self._config: Dict[str, Any] = {}
        self._load()

    def _load(self):
        """Load and merge all config layers."""
        self._config = {}

        for config_dir in settings.config_dirs:
            config_file = config_dir / "config.yaml"
            if config_file.exists():
                try:
                    data = yaml.safe_load(config_file.read_text()) or {}
                    self._config = self._deep_merge(self._config, data)
                except Exception as e:
                    logger.warning("config_load_error", path=str(config_file), error=str(e))

    def get(self, key: str, default: Any = None) -> Any:
        """Get config value by dot-notation key."""
        parts = key.split(".")
        value = self._config
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            else:
                return default
            if value is None:
                return default
        return value

    def set(self, key: str, value: Any):
        """Set a config value (in-memory only)."""
        parts = key.split(".")
        target = self._config
        for part in parts[:-1]:
            if part not in target or not isinstance(target[part], dict):
                target[part] = {}
            target = target[part]
        target[parts[-1]] = value

    def get_all(self) -> Dict[str, Any]:
        """Get the full merged config."""
        return self._config.copy()

    def reload(self):
        """Reload config from disk."""
        self._load()

    @staticmethod
    def _deep_merge(base: dict, override: dict) -> dict:
        """Deep merge two dictionaries (override wins)."""
        result = base.copy()
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = ConfigHierarchy._deep_merge(result[key], value)
            else:
                result[key] = value
        return result


# Singleton
config_hierarchy = ConfigHierarchy()
