"""Output Validator — Validate generated code and files."""

import ast
import json
from typing import Optional

import structlog

logger = structlog.get_logger()


class OutputValidator:
    """Validate outputs from agent tool execution."""

    async def validate_python(self, code: str) -> dict:
        """Validate Python code syntax."""
        try:
            ast.parse(code)
            return {"valid": True, "errors": []}
        except SyntaxError as e:
            return {"valid": False, "errors": [f"Line {e.lineno}: {e.msg}"]}

    async def validate_json(self, content: str) -> dict:
        """Validate JSON content."""
        try:
            json.loads(content)
            return {"valid": True, "errors": []}
        except json.JSONDecodeError as e:
            return {"valid": False, "errors": [str(e)]}

    async def validate_file_output(self, path: str, content: str) -> dict:
        """Validate file output based on extension."""
        if path.endswith(".py"):
            return await self.validate_python(content)
        elif path.endswith(".json"):
            return await self.validate_json(content)
        # Add more validators as needed
        return {"valid": True, "errors": []}


# Global instance
output_validator = OutputValidator()
