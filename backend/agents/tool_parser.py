"""
MiLyfe Brain - Tool Call Parser

Parses tool calls from LLM output in multiple formats:
- JSON code blocks
- Inline JSON objects
- XML-style <tool_call> tags
- ReAct format (Action: / Action Input:)

Handles common JSON issues like trailing commas and unquoted keys.
"""
from __future__ import annotations

import json
import logging
import re
from typing import List, Optional

from models.schemas import ToolCall

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tool name key variants
# ---------------------------------------------------------------------------
_TOOL_NAME_KEYS = ("tool", "tool_name", "name", "function")

# Argument key variants
_ARGS_KEYS = ("args", "arguments", "parameters", "input", "params")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def parse_tool_calls(text: str) -> List[ToolCall]:
    """
    Parse tool calls from LLM output, trying multiple formats in order.

    Returns a list of ToolCall objects. Returns empty list if no tool calls found.
    """
    if not text or not text.strip():
        return []

    # Try each format in order of specificity
    results = _parse_json_blocks(text)
    if results:
        return results

    results = _parse_xml_style(text)
    if results:
        return results

    results = _parse_react_format(text)
    if results:
        return results

    results = _parse_inline_json(text)
    if results:
        return results

    return []


# ---------------------------------------------------------------------------
# Format Parsers
# ---------------------------------------------------------------------------


def _parse_json_blocks(text: str) -> List[ToolCall]:
    """Parse tool calls from ```json {...} ``` code blocks."""
    pattern = r"```(?:json)?\s*\n?\s*(\{[^`]*?\})\s*\n?\s*```"
    matches = re.findall(pattern, text, re.DOTALL)

    results: List[ToolCall] = []
    for match in matches:
        tc = _try_parse_json_tool_call(match)
        if tc is not None:
            results.append(tc)

    return results


def _parse_inline_json(text: str) -> List[ToolCall]:
    """
    Parse inline JSON objects that look like tool calls.

    Matches: {"tool": "name", "args": {...}}
    """
    # Find JSON objects that contain a tool name key
    pattern = r'\{[^{}]*"(?:tool|tool_name|name|function)"[^{}]*\}'
    matches = re.findall(pattern, text)

    results: List[ToolCall] = []
    for match in matches:
        tc = _try_parse_json_tool_call(match)
        if tc is not None:
            results.append(tc)

    # Also try to find nested JSON objects (with inner braces for args)
    if not results:
        nested_pattern = r'\{[^{}]*"(?:tool|tool_name|name|function)"[^{}]*\{[^{}]*\}[^{}]*\}'
        nested_matches = re.findall(nested_pattern, text)
        for match in nested_matches:
            tc = _try_parse_json_tool_call(match)
            if tc is not None:
                results.append(tc)

    return results


def _parse_xml_style(text: str) -> List[ToolCall]:
    """Parse tool calls from <tool_call>JSON</tool_call> tags."""
    pattern = r"<tool_call>\s*(.*?)\s*</tool_call>"
    matches = re.findall(pattern, text, re.DOTALL)

    results: List[ToolCall] = []
    for match in matches:
        tc = _try_parse_json_tool_call(match.strip())
        if tc is not None:
            results.append(tc)

    return results


def _parse_react_format(text: str) -> List[ToolCall]:
    """
    Parse ReAct-style tool calls:
      Action: tool_name
      Action Input: {"key": "value"}
    """
    pattern = r"Action:\s*(.+?)\s*\n\s*Action Input:\s*(.+?)(?:\n|$)"
    matches = re.findall(pattern, text, re.DOTALL)

    results: List[ToolCall] = []
    for tool_name, args_str in matches:
        tool_name = tool_name.strip()
        args_str = args_str.strip()

        # Try to parse the action input as JSON
        args = _safe_json_parse(args_str)
        if args is None:
            # Treat as a single string argument
            args = {"input": args_str}

        results.append(
            ToolCall(
                tool_name=tool_name,
                arguments=args if isinstance(args, dict) else {"input": args},
            )
        )

    return results


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _try_parse_json_tool_call(json_str: str) -> Optional[ToolCall]:
    """
    Attempt to parse a JSON string into a ToolCall.

    Handles multiple key naming conventions for tool name and arguments.
    """
    data = _safe_json_parse(json_str)
    if data is None or not isinstance(data, dict):
        return None

    # Extract tool name
    tool_name: Optional[str] = None
    for key in _TOOL_NAME_KEYS:
        if key in data:
            tool_name = str(data[key])
            break

    if not tool_name:
        return None

    # Extract arguments
    arguments: dict = {}
    for key in _ARGS_KEYS:
        if key in data:
            val = data[key]
            if isinstance(val, dict):
                arguments = val
            elif isinstance(val, str):
                # Try parsing string value as JSON
                parsed = _safe_json_parse(val)
                arguments = parsed if isinstance(parsed, dict) else {"input": val}
            break

    # If no args key found, use remaining keys as arguments
    if not arguments:
        excluded_keys = set(_TOOL_NAME_KEYS) | set(_ARGS_KEYS) | {"id", "type"}
        arguments = {k: v for k, v in data.items() if k not in excluded_keys}

    return ToolCall(
        tool_name=tool_name,
        arguments=arguments,
    )


def _safe_json_parse(text: str) -> Optional[any]:
    """
    Attempt to parse JSON with fixups for common LLM issues.

    Handles:
    - Trailing commas
    - Single quotes (converts to double)
    - Unquoted keys
    """
    if not text or not text.strip():
        return None

    text = text.strip()

    # First, try direct parsing
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Fix trailing commas before } or ]
    fixed = re.sub(r",\s*([}\]])", r"\1", text)
    try:
        return json.loads(fixed)
    except json.JSONDecodeError:
        pass

    # Try replacing single quotes with double quotes (naive approach)
    fixed_quotes = text.replace("'", '"')
    fixed_quotes = re.sub(r",\s*([}\]])", r"\1", fixed_quotes)
    try:
        return json.loads(fixed_quotes)
    except json.JSONDecodeError:
        pass

    # Try to fix unquoted keys: {key: "value"} -> {"key": "value"}
    fixed_keys = re.sub(r"(\{|,)\s*(\w+)\s*:", r'\1 "\2":', text)
    fixed_keys = re.sub(r",\s*([}\]])", r"\1", fixed_keys)
    try:
        return json.loads(fixed_keys)
    except json.JSONDecodeError:
        pass

    logger.debug(f"Failed to parse JSON after all fixups: {text[:100]}")
    return None
