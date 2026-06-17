"""MiLyfe Brain — Plugin Loader (Dynamic discovery + registration)."""

from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

import structlog

logger = structlog.get_logger()


class PluginLoader:
    """Discovers and loads plugins from the plugins directory."""

    def __init__(self, plugins_dir: str = None):
        self._plugins_dir = Path(plugins_dir or "/app/plugins")
        self._loaded: Dict[str, Dict[str, Any]] = {}

    def discover(self) -> List[Dict[str, Any]]:
        """Discover available plugins."""
        plugins = []
        if not self._plugins_dir.exists():
            return plugins

        for plugin_dir in self._plugins_dir.iterdir():
            if not plugin_dir.is_dir():
                continue
            manifest_path = plugin_dir / "manifest.json"
            if not manifest_path.exists():
                continue

            try:
                manifest = json.loads(manifest_path.read_text())
                manifest["path"] = str(plugin_dir)
                plugins.append(manifest)
            except Exception as e:
                logger.warning("plugin_manifest_error", path=str(plugin_dir), error=str(e))

        return plugins

    def load(self, plugin_name: str) -> bool:
        """Load and activate a plugin."""
        plugins = self.discover()
        plugin = next((p for p in plugins if p.get("name") == plugin_name), None)
        if not plugin:
            logger.error("plugin_not_found", name=plugin_name)
            return False

        plugin_path = Path(plugin["path"])
        plugin_file = plugin_path / "plugin.py"

        if not plugin_file.exists():
            logger.error("plugin_file_missing", path=str(plugin_file))
            return False

        try:
            # Add plugin to path and import
            sys.path.insert(0, str(plugin_path))
            module = importlib.import_module("plugin")

            # Call register function if it exists
            if hasattr(module, "register"):
                from tools.registry import tool_registry
                module.register(tool_registry)

            self._loaded[plugin_name] = {
                "manifest": plugin,
                "module": module,
            }
            logger.info("plugin_loaded", name=plugin_name)
            return True

        except Exception as e:
            logger.error("plugin_load_error", name=plugin_name, error=str(e))
            return False
        finally:
            sys.path.pop(0)

    def unload(self, plugin_name: str):
        """Unload a plugin."""
        if plugin_name in self._loaded:
            module = self._loaded[plugin_name].get("module")
            if module and hasattr(module, "unregister"):
                module.unregister()
            del self._loaded[plugin_name]

    def list_loaded(self) -> List[str]:
        """List loaded plugins."""
        return list(self._loaded.keys())


# Singleton
plugin_loader = PluginLoader()
