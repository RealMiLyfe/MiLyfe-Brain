"""MiLyfe Brain — Parse Tool Calls from LLM Output.

Supports multiple formats:
1. JSON blocks: {"tool": "name", "args": {...}}
2. Markdown code blocks with JSON
3. XML-style: <tool_call>...</tool_call>
4. ReAct format: Action: tool_name\nAction Input: {...}
"""

from __future__ import annotations

import json
import re
from typing import List

import structlog

from models.schemas import ToolCall

logger = structlog.get_logger()


def parse_tool_calls(text: str) -> List[ToolCall]:
    """Parse tool calls from LLM response text.

    Tries multiple formats in order of specificity.
    """
    calls = []

    # Try JSON code blocks first (most explicit)
    calls = _parse_json_blocks(text)
    if calls:
        return calls

    # Try inline JSON objects
    calls = _parse_inline_json(text)
    if calls:
        return calls

    # Try XML-style
    calls = _parse_xml_style(text)
    if calls:
        return calls

    # Try ReAct format
    calls = _parse_react_format(text)
    if calls:
        return calls

    return []


def _parse_json_blocks(text: str) -> List[ToolCall]:
    """Parse JSON from markdown code blocks."""
    calls = []
    # Match ```json ... ``` blocks
    pattern = r"```(?:json)?\s*\n?(\{[^`]+\})\s*\n?```"
    matches = re.findall(pattern, text, re.DOTALL)

    for match in matches:
        tc = _try_parse_json_tool_call(match)
        if tc:
            calls.append(tc)

    return calls


def _parse_inline_json(text: str) -> List[ToolCall]:
    """Parse inline JSON objects that look like tool calls."""
    calls = []
    # Match JSON objects with "tool" key
    pattern = r'\{[^{}]*"tool"\s*:\s*"[^"]+?"[^{}]*\}'
    matches = re.findall(pattern, text)

    for match in matches:
        tc = _try_parse_json_tool_call(match)
        if tc:
            calls.append(tc)

    return calls


def _parse_xml_style(text: str) -> List[ToolCall]:
    """Parse XML-style tool calls: <tool_call>JSON</tool_call>."""
    calls = []
    pattern = r"<tool_call>\s*(.+?)\s*</tool_call>"
    matches = re.findall(pattern, text, re.DOTALL)

    for match in matches:
        tc = _try_parse_json_tool_call(match)
        if tc:
            calls.append(tc)

    return calls


def _parse_react_format(text: str) -> List[ToolCall]:
    """Parse ReAct format: Action: name / Action Input: {...}."""
    calls = []
    # Match Action: tool_name\nAction Input: {...}
    pattern = r"Action:\s*(\w+)\s*\n\s*Action Input:\s*(\{.+?\})"
    matches = re.findall(pattern, text, re.DOTALL)

    for tool_name, args_str in matches:
        try:
            args = json.loads(args_str)
            calls.append(ToolCall(tool_name=tool_name, arguments=args))
        except json.JSONDecodeError:
            # Try with relaxed parsing
            calls.append(ToolCall(tool_name=tool_name, arguments={"input": args_str}))

    return calls


def _try_parse_json_tool_call(json_str: str) -> ToolCall | None:
    """Try to parse a JSON string as a tool call."""
    try:
        data = json.loads(json_str)
    except json.JSONDecodeError:
        # Try fixing common JSON issues
        try:
            # Remove trailing commas
            fixed = re.sub(r",\s*}", "}", json_str)
            fixed = re.sub(r",\s*]", "]", fixed)
            data = json.loads(fixed)
        except json.JSONDecodeError:
            return None

    if not isinstance(data, dict):
        return None

    # Extract tool name (various key formats)
    tool_name = (
        data.get("tool")
        or data.get("tool_name")
        or data.get("name")
        or data.get("function")
    )
    if not tool_name:
        return None

    # Extract arguments
    arguments = (
        data.get("args")
        or data.get("arguments")
        or data.get("parameters")
        or data.get("input")
        or data.get("params")
        or {}
    )
    if isinstance(arguments, str):
        arguments = {"input": arguments}

    return ToolCall(
        tool_name=str(tool_name),
        arguments=arguments if isinstance(arguments, dict) else {},
        call_id=data.get("id"),
    )
