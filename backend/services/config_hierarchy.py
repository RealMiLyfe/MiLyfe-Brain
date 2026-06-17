"""Configuration Hierarchy — Multi-layer config cascade.

4 layers: system defaults → ~/.milyfe/config.yaml → workspace config → subdirectory config
"""

from pathlib import Path
from typing import Any, Optional

import yaml
import structlog

from config import settings

logger = structlog.get_logger()


class ConfigHierarchy:
    """Multi-layer configuration with dot-notation access."""

    def __init__(self):
        self._config: dict = {}
        self._loaded: bool = False

    def load(self) -> None:
        """Load configuration from all layers."""
        self._config = self._get_defaults()

        # Layer 2: User config
        user_config = Path.home() / ".milyfe" / "config.yaml"
        if user_config.exists():
            self._merge(self._load_yaml(user_config))

        # Layer 3: Workspace config
        ws_config = Path(settings.workspace_dir) / ".milyfe" / "config.yaml"
        if ws_config.exists():
            self._merge(self._load_yaml(ws_config))

        self._loaded = True

    def get(self, key: str, default: Any = None) -> Any:
        """Get config value using dot notation (e.g., 'models.heavy')."""
        if not self._loaded:
            self.load()

        parts = key.split(".")
        current = self._config

        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return default

        return current

    def set(self, key: str, value: Any) -> None:
        """Set a config value."""
        parts = key.split(".")
        current = self._config

        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]

        current[parts[-1]] = value

    def _get_defaults(self) -> dict:
        """System defaults."""
        return {
            "models": {
                "light": settings.default_light_model,
                "heavy": settings.default_heavy_model,
                "premium": settings.premium_model,
            },
            "safety": {
                "require_approval_destructive": settings.require_approval_destructive,
                "require_approval_browsing": settings.require_approval_browsing,
                "require_approval_gui": settings.require_approval_gui,
            },
            "behavior": {
                "max_retries": settings.max_retries,
                "agent_timeout": settings.agent_timeout,
                "auto_git_snapshots": settings.auto_git_snapshots,
            },
            "output": {
                "style": "default",
                "max_response_length": 10000,
            },
        }

    def _load_yaml(self, path: Path) -> dict:
        """Load YAML config file."""
        try:
            with open(path) as f:
                data = yaml.safe_load(f)
                return data if isinstance(data, dict) else {}
        except Exception as e:
            logger.warning("Config load failed", path=str(path), error=str(e))
            return {}

    def _merge(self, override: dict) -> None:
        """Deep merge override into config."""
        self._config = self._deep_merge(self._config, override)

    def _deep_merge(self, base: dict, override: dict) -> dict:
        result = base.copy()
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result


# Global instance
config_hierarchy = ConfigHierarchy()
