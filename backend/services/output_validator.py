"""MiLyfe Brain — Output Validator (validate generated code/files)."""

from __future__ import annotations

import asyncio
import json
import re
from pathlib import Path
from typing import Dict, List, Tuple

import structlog

logger = structlog.get_logger()


class OutputValidator:
    """Validates generated code and files for common issues."""

    async def validate_file(self, path: str, content: str) -> Tuple[bool, List[str]]:
        """Validate a generated file. Returns (valid, issues)."""
        issues = []

        # Check file isn't empty
        if not content.strip():
            issues.append("File is empty")
            return False, issues

        # Extension-specific validation
        ext = Path(path).suffix.lower()

        if ext == ".py":
            issues.extend(self._validate_python(content))
        elif ext == ".json":
            issues.extend(self._validate_json(content))
        elif ext in (".ts", ".tsx", ".js", ".jsx"):
            issues.extend(self._validate_javascript(content))
        elif ext in (".yaml", ".yml"):
            issues.extend(self._validate_yaml(content))

        # Generic checks
        if len(content) > 1_000_000:
            issues.append("File exceeds 1MB")
        if "\x00" in content:
            issues.append("File contains null bytes")

        return len(issues) == 0, issues

    def _validate_python(self, content: str) -> List[str]:
        """Validate Python syntax."""
        issues = []
        try:
            compile(content, "<string>", "exec")
        except SyntaxError as e:
            issues.append(f"Python syntax error: {e}")
        return issues

    def _validate_json(self, content: str) -> List[str]:
        """Validate JSON."""
        issues = []
        try:
            json.loads(content)
        except json.JSONDecodeError as e:
            issues.append(f"Invalid JSON: {e}")
        return issues

    def _validate_javascript(self, content: str) -> List[str]:
        """Basic JavaScript/TypeScript validation."""
        issues = []
        # Check for unmatched braces
        opens = content.count("{") + content.count("(") + content.count("[")
        closes = content.count("}") + content.count(")") + content.count("]")
        if abs(opens - closes) > 2:
            issues.append(f"Possibly unmatched brackets (open={opens}, close={closes})")
        return issues

    def _validate_yaml(self, content: str) -> List[str]:
        """Validate YAML."""
        issues = []
        try:
            import yaml
            yaml.safe_load(content)
        except Exception as e:
            issues.append(f"Invalid YAML: {e}")
        return issues


# Singleton
output_validator = OutputValidator()
