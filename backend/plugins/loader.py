"""Dynamic plugin discovery and loading for MiLyfe Brain."""

import importlib
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from config import settings

logger = logging.getLogger(__name__)


class PluginBase:
    """Base class for all plugins."""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.logger = logging.getLogger(f"plugin.{self.__class__.__name__}")
    
    async def on_load(self):
        """Called when the plugin is loaded."""
        pass
    
    async def on_unload(self):
        """Called when the plugin is unloaded."""
        pass


class PluginLoader:
    """Discovers, loads, and manages plugins."""
    
    def __init__(self):
        self._plugins: Dict[str, PluginBase] = {}
        self._plugin_dirs = [
            Path(settings.workspace_dir) / ".milyfe" / "plugins",
            Path.home() / ".milyfe" / "plugins",
            Path(__file__).parent,  # Built-in plugins
        ]
    
    async def discover_and_load(self) -> List[str]:
        """Discover and load all available plugins."""
        loaded = []
        for plugin_dir in self._plugin_dirs:
            if not plugin_dir.exists():
                continue
            for item in plugin_dir.iterdir():
                if item.is_dir() and (item / "manifest.json").exists():
                    try:
                        name = await self._load_plugin(item)
                        if name:
                            loaded.append(name)
                    except Exception as e:
                        logger.error(f"Failed to load plugin from {item}: {e}")
        return loaded
    
    async def _load_plugin(self, plugin_dir: Path) -> Optional[str]:
        """Load a single plugin from its directory."""
        manifest_path = plugin_dir / "manifest.json"
        manifest = json.loads(manifest_path.read_text())
        
        name = manifest.get("name", plugin_dir.name)
        entry = manifest.get("entry", "plugin.py")
        config = manifest.get("config_schema", {})
        
        plugin_file = plugin_dir / entry
        if not plugin_file.exists():
            logger.warning(f"Plugin entry point not found: {plugin_file}")
            return None
        
        # Load the module
        spec = importlib.util.spec_from_file_location(f"plugins.{name}", str(plugin_file))
        if spec is None or spec.loader is None:
            return None
        
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Find the plugin class (first subclass of PluginBase)
        plugin_class = None
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if (isinstance(attr, type) and issubclass(attr, PluginBase) 
                and attr is not PluginBase):
                plugin_class = attr
                break
        
        if plugin_class is None:
            logger.warning(f"No PluginBase subclass found in {plugin_file}")
            return None
        
        # Instantiate and load
        instance = plugin_class(config=config)
        await instance.on_load()
        self._plugins[name] = instance
        
        logger.info(f"Loaded plugin: {name} (tools: {manifest.get('tools', [])})")
        return name
    
    async def unload(self, name: str) -> bool:
        """Unload a plugin by name."""
        plugin = self._plugins.get(name)
        if plugin:
            await plugin.on_unload()
            del self._plugins[name]
            return True
        return False
    
    async def unload_all(self):
        """Unload all plugins."""
        for name in list(self._plugins.keys()):
            await self.unload(name)
    
    def get(self, name: str) -> Optional[PluginBase]:
        """Get a loaded plugin by name."""
        return self._plugins.get(name)
    
    def list_loaded(self) -> List[Dict[str, Any]]:
        """List all loaded plugins."""
        return [
            {"name": name, "class": type(plugin).__name__}
            for name, plugin in self._plugins.items()
        ]


# Singleton
plugin_loader = PluginLoader()
