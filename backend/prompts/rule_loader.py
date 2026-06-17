"""MiLyfe Brain — Hierarchical Rule Loader.

Loads .rules YAML files from multiple layers with deep merge semantics.
Later layers override earlier ones (system < user < workspace).
"""

from __future__ import annotations

import logging
import os
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

logger = logging.getLogger(__name__)

# Default system rules (baseline)
_SYSTEM_DEFAULTS: Dict[str, Any] = {
    "safety": {
        "require_approval_destructive": True,
        "require_approval_browsing": True,
        "blocked_commands": ["rm -rf /", "dd if=/dev/zero"],
    },
    "agents": {
        "max_concurrent": 5,
        "timeout_seconds": 300,
        "retry_count": 3,
    },
    "output": {
        "default_style": "default",
        "max_response_tokens": 4096,
        "include_sources": True,
    },
    "tools": {
        "enabled": ["file_read", "file_write", "shell_exec", "grep_search", "glob_search"],
        "disabled": [],
    },
}


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Deep merge two dicts. Values in override take precedence.

    For nested dicts, merging is recursive. For other types
    (including lists), the override value replaces the base.

    Args:
        base: The base dictionary.
        override: The override dictionary.

    Returns:
        A new merged dictionary.
    """
    result = deepcopy(base)
    for key, value in override.items():
        if (
            key in result
            and isinstance(result[key], dict)
            and isinstance(value, dict)
        ):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = deepcopy(value)
    return result


class RuleLoader:
    """Loads and merges hierarchical .rules YAML configuration.

    Loading order (later overrides earlier):
    1. System defaults (built-in)
    2. User-level rules (~/.milyfe/rules/*.yaml)
    3. Workspace-level rules (<workspace>/.milyfe/rules/*.yaml)
    """

    def __init__(self) -> None:
        self._cache: Dict[str, Dict[str, Any]] = {}

    def load_rules(self, workspace_path: str) -> Dict[str, Any]:
        """Load and merge rules from all layers.

        Args:
            workspace_path: Path to the workspace directory.

        Returns:
            Merged configuration dictionary.
        """
        # Check cache
        if workspace_path in self._cache:
            return self._cache[workspace_path]

        # Start with system defaults
        merged = deepcopy(_SYSTEM_DEFAULTS)

        # Layer 2: User-level rules
        user_rules_dir = Path.home() / ".milyfe" / "rules"
        user_rules = self._load_rules_from_dir(user_rules_dir)
        if user_rules:
            merged = _deep_merge(merged, user_rules)

        # Layer 3: Workspace-level rules
        workspace_rules_dir = Path(workspace_path) / ".milyfe" / "rules"
        workspace_rules = self._load_rules_from_dir(workspace_rules_dir)
        if workspace_rules:
            merged = _deep_merge(merged, workspace_rules)

        # Cache the result
        self._cache[workspace_path] = merged
        return merged

    def _load_rules_from_dir(self, rules_dir: Path) -> Dict[str, Any]:
        """Load all YAML rule files from a directory and merge them.

        Args:
            rules_dir: Path to the rules directory.

        Returns:
            Merged dict of all rule files in the directory.
        """
        if not rules_dir.exists() or not rules_dir.is_dir():
            return {}

        merged: Dict[str, Any] = {}
        yaml_files = sorted(rules_dir.glob("*.yaml")) + sorted(rules_dir.glob("*.yml"))

        for yaml_file in yaml_files:
            try:
                content = yaml_file.read_text(encoding="utf-8")
                data = yaml.safe_load(content)
                if isinstance(data, dict):
                    merged = _deep_merge(merged, data)
                    logger.debug(f"Loaded rules from {yaml_file}")
            except yaml.YAMLError as e:
                logger.warning(f"Failed to parse {yaml_file}: {e}")
            except OSError as e:
                logger.warning(f"Failed to read {yaml_file}: {e}")

        return merged

    def invalidate_cache(self, workspace_path: Optional[str] = None) -> None:
        """Clear the rules cache.

        Args:
            workspace_path: If provided, only clear cache for this workspace.
                If None, clear all cached rules.
        """
        if workspace_path:
            self._cache.pop(workspace_path, None)
        else:
            self._cache.clear()

    def get_rule(self, workspace_path: str, *keys: str, default: Any = None) -> Any:
        """Get a specific nested rule value using dot-path keys.

        Args:
            workspace_path: Path to the workspace.
            *keys: Sequence of keys to traverse (e.g., 'safety', 'blocked_commands').
            default: Default value if the key path doesn't exist.

        Returns:
            The value at the specified path, or the default.
        """
        rules = self.load_rules(workspace_path)
        current = rules
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return default
        return current
