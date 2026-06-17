"""Plugin Loader — Dynamic plugin discovery and loading."""

import importlib
import json
from pathlib import Path
from typing import Any

import structlog

logger = structlog.get_logger()


class PluginManifest:
    """Parsed plugin manifest."""

    def __init__(self, data: dict):
        self.name = data.get("name", "unknown")
        self.version = data.get("version", "0.0.1")
        self.description = data.get("description", "")
        self.author = data.get("author", "")
        self.entry_point = data.get("entry_point", "plugin.py")
        self.tools = data.get("tools", [])
        self.permissions = data.get("permissions", [])


class PluginLoader:
    """Discover and load plugins from plugin directories."""

    def __init__(self):
        self._plugins: dict[str, dict] = {}
        self._plugin_dir = Path(__file__).parent

    def discover(self) -> list[PluginManifest]:
        """Discover all plugins with manifest.json files."""
        manifests = []

        for item in self._plugin_dir.iterdir():
            if item.is_dir() and (item / "manifest.json").exists():
                try:
                    with open(item / "manifest.json") as f:
                        data = json.load(f)
                    manifest = PluginManifest(data)
                    manifests.append(manifest)
                    logger.info("Plugin discovered", name=manifest.name, version=manifest.version)
                except Exception as e:
                    logger.warning("Plugin manifest parse failed", dir=item.name, error=str(e))

        return manifests

    def load(self, plugin_name: str) -> bool:
        """Load a specific plugin."""
        plugin_dir = self._plugin_dir / plugin_name

        if not plugin_dir.exists():
            logger.error("Plugin not found", name=plugin_name)
            return False

        manifest_path = plugin_dir / "manifest.json"
        if not manifest_path.exists():
            logger.error("Plugin manifest not found", name=plugin_name)
            return False

        try:
            with open(manifest_path) as f:
                manifest = PluginManifest(json.load(f))

            # Dynamic import
            entry_point = plugin_dir / manifest.entry_point
            if entry_point.exists():
                spec = importlib.util.spec_from_file_location(f"plugins.{plugin_name}", str(entry_point))
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                # Register tools if plugin has them
                if hasattr(module, "register"):
                    from tools.registry import tool_registry
                    module.register(tool_registry)

                self._plugins[plugin_name] = {"manifest": manifest, "module": module}
                logger.info("Plugin loaded", name=plugin_name)
                return True

        except Exception as e:
            logger.error("Plugin load failed", name=plugin_name, error=str(e))

        return False

    def load_all(self) -> int:
        """Load all discovered plugins."""
        manifests = self.discover()
        loaded = 0
        for manifest in manifests:
            if self.load(manifest.name):
                loaded += 1
        return loaded

    def list_loaded(self) -> list[dict]:
        """List all loaded plugins."""
        return [
            {"name": name, "version": info["manifest"].version, "description": info["manifest"].description}
            for name, info in self._plugins.items()
        ]


# Global instance
plugin_loader = PluginLoader()
