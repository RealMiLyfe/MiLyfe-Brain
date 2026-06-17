"""MiLyfe Brain — Plugin System.

Provides dynamic plugin discovery, loading, and lifecycle management.
Plugins extend Brain functionality through a manifest-based architecture.
"""

from plugins.loader import PluginBase, PluginLoader, plugin_loader

__all__ = [
    "PluginBase",
    "PluginLoader",
    "plugin_loader",
]
