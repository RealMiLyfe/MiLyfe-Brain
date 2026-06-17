"""Tool Call Parser — Extract tool calls from LLM output.

Supports multiple formats: JSON, markdown code blocks, XML, ReAct.
"""

import json
import re
from typing import Any

import structlog

logger = structlog.get_logger()


class ToolParser:
    """Parse tool calls from various LLM output formats."""

    # Patterns for different tool call formats
    JSON_PATTERN = re.compile(
        r'\{\s*"tool"\s*:\s*"([^"]+)"\s*,\s*"params"\s*:\s*(\{[^}]*\})\s*\}',
        re.DOTALL,
    )

    MARKDOWN_JSON_PATTERN = re.compile(
        r"```(?:json)?\s*\n(\{[^`]*\})\s*\n```",
        re.DOTALL,
    )

    XML_PATTERN = re.compile(
        r"<tool_call>\s*<name>(.*?)</name>\s*<arguments>(.*?)</arguments>\s*</tool_call>",
        re.DOTALL,
    )

    REACT_PATTERN = re.compile(
        r"Action:\s*(\w+)\s*\nAction Input:\s*(.+?)(?:\n|$)",
        re.DOTALL,
    )

    @classmethod
    def parse(cls, text: str) -> list[dict[str, Any]]:
        """Parse tool calls from LLM response text.

        Tries multiple formats in order of specificity.
        Returns list of {"name": str, "params": dict}.
        """
        tool_calls = []

        # Try XML format first (most structured)
        xml_calls = cls._parse_xml(text)
        if xml_calls:
            return xml_calls

        # Try markdown JSON blocks
        md_calls = cls._parse_markdown_json(text)
        if md_calls:
            return md_calls

        # Try inline JSON format
        json_calls = cls._parse_json(text)
        if json_calls:
            return json_calls

        # Try ReAct format
        react_calls = cls._parse_react(text)
        if react_calls:
            return react_calls

        return tool_calls

    @classmethod
    def _parse_json(cls, text: str) -> list[dict]:
        """Parse {"tool": "name", "params": {...}} format."""
        results = []
        for match in cls.JSON_PATTERN.finditer(text):
            try:
                tool_name = match.group(1)
                params_str = match.group(2)
                params = json.loads(params_str)
                results.append({"name": tool_name, "params": params})
            except (json.JSONDecodeError, IndexError) as e:
                logger.debug("JSON parse failed", error=str(e))
        return results

    @classmethod
    def _parse_markdown_json(cls, text: str) -> list[dict]:
        """Parse JSON within markdown code blocks."""
        results = []
        for match in cls.MARKDOWN_JSON_PATTERN.finditer(text):
            try:
                data = json.loads(match.group(1))
                if "tool" in data and "params" in data:
                    results.append({"name": data["tool"], "params": data["params"]})
                elif "name" in data and "arguments" in data:
                    results.append({"name": data["name"], "params": data["arguments"]})
            except (json.JSONDecodeError, KeyError) as e:
                logger.debug("Markdown JSON parse failed", error=str(e))
        return results

    @classmethod
    def _parse_xml(cls, text: str) -> list[dict]:
        """Parse <tool_call><name>...</name><arguments>...</arguments></tool_call>."""
        results = []
        for match in cls.XML_PATTERN.finditer(text):
            try:
                tool_name = match.group(1).strip()
                args_str = match.group(2).strip()
                params = json.loads(args_str) if args_str else {}
                results.append({"name": tool_name, "params": params})
            except (json.JSONDecodeError, IndexError) as e:
                logger.debug("XML parse failed", error=str(e))
        return results

    @classmethod
    def _parse_react(cls, text: str) -> list[dict]:
        """Parse ReAct format: Action: tool_name\nAction Input: {...}."""
        results = []
        for match in cls.REACT_PATTERN.finditer(text):
            try:
                tool_name = match.group(1).strip()
                input_str = match.group(2).strip()
                try:
                    params = json.loads(input_str)
                except json.JSONDecodeError:
                    params = {"input": input_str}
                results.append({"name": tool_name, "params": params})
            except (IndexError, AttributeError) as e:
                logger.debug("ReAct parse failed", error=str(e))
        return results
