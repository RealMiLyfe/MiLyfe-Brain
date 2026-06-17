"""Parse tool calls from LLM output in multiple formats.

Supports: JSON blocks, markdown code blocks, XML-style, ReAct format.
Returns structured ToolCall dataclass instances.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import logging

logger = logging.getLogger(__name__)


@dataclass
class ToolCall:
    """Represents a parsed tool call from LLM output."""

    name: str
    arguments: Dict[str, Any] = field(default_factory=dict)


def parse_tool_calls(text: str) -> List[ToolCall]:
    """Parse tool calls from LLM output using multiple format strategies.

    Tries formats in order of specificity:
    1. JSON code blocks (```json ... ```)
    2. XML-style tool calls (<tool_call>...</tool_call>)
    3. ReAct format (Action: ... Action Input: ...)
    4. Inline JSON objects with tool_call/function_call keys
    5. Raw JSON array of tool calls

    Returns:
        List of ToolCall instances. Empty list if no tool calls found.
    """
    if not text or not text.strip():
        return []

    # Try each parser in order, return first successful result
    parsers = [
        _parse_json_code_blocks,
        _parse_xml_style,
        _parse_react_format,
        _parse_inline_json,
        _parse_raw_json_array,
    ]

    for parser in parsers:
        try:
            result = parser(text)
            if result:
                logger.debug(
                    "Parsed %d tool call(s) using %s", len(result), parser.__name__
                )
                return result
        except Exception as e:
            logger.debug("Parser %s failed: %s", parser.__name__, e)
            continue

    return []


def _parse_json_code_blocks(text: str) -> List[ToolCall]:
    """Parse tool calls from ```json code blocks."""
    pattern = r"```(?:json)?\s*\n?(.*?)\n?\s*```"
    matches = re.findall(pattern, text, re.DOTALL)

    tool_calls: List[ToolCall] = []

    for match in matches:
        match = match.strip()
        if not match:
            continue

        try:
            data = json.loads(match)
        except json.JSONDecodeError:
            continue

        calls = _extract_tool_calls_from_data(data)
        tool_calls.extend(calls)

    return tool_calls


def _parse_xml_style(text: str) -> List[ToolCall]:
    """Parse XML-style tool calls.

    Formats supported:
    <tool_call>{"name": "...", "arguments": {...}}</tool_call>
    <function_call name="...">{"arg": "val"}</function_call>
    """
    tool_calls: List[ToolCall] = []

    # Pattern 1: <tool_call>JSON</tool_call>
    pattern1 = r"<tool_call>\s*(.*?)\s*</tool_call>"
    for match in re.finditer(pattern1, text, re.DOTALL):
        content = match.group(1).strip()
        try:
            data = json.loads(content)
            call = _data_to_tool_call(data)
            if call:
                tool_calls.append(call)
        except json.JSONDecodeError:
            continue

    # Pattern 2: <function_call name="...">JSON</function_call>
    pattern2 = r'<function_call\s+name=["\']([^"\']+)["\']\s*>(.*?)</function_call>'
    for match in re.finditer(pattern2, text, re.DOTALL):
        name = match.group(1).strip()
        args_str = match.group(2).strip()
        try:
            arguments = json.loads(args_str) if args_str else {}
        except json.JSONDecodeError:
            arguments = {}
        tool_calls.append(ToolCall(name=name, arguments=arguments))

    # Pattern 3: <tool name="...">JSON</tool>
    pattern3 = r'<tool\s+name=["\']([^"\']+)["\']\s*>(.*?)</tool>'
    for match in re.finditer(pattern3, text, re.DOTALL):
        name = match.group(1).strip()
        args_str = match.group(2).strip()
        try:
            arguments = json.loads(args_str) if args_str else {}
        except json.JSONDecodeError:
            arguments = {}
        tool_calls.append(ToolCall(name=name, arguments=arguments))

    return tool_calls


def _parse_react_format(text: str) -> List[ToolCall]:
    """Parse ReAct-style format.

    Format:
    Thought: ...
    Action: tool_name
    Action Input: {"arg": "value"}
    """
    tool_calls: List[ToolCall] = []

    # Find all Action/Action Input pairs
    pattern = r"Action:\s*(.+?)(?:\n|$)\s*Action\s*Input:\s*(.*?)(?:\n(?=(?:Thought:|Action:|Observation:|$))|$)"
    matches = re.finditer(pattern, text, re.DOTALL | re.IGNORECASE)

    for match in matches:
        name = match.group(1).strip()
        args_str = match.group(2).strip()

        # Clean up the name (remove quotes if present)
        name = name.strip("\"'`")

        # Parse arguments
        arguments: Dict[str, Any] = {}
        if args_str:
            try:
                arguments = json.loads(args_str)
            except json.JSONDecodeError:
                # Try to extract key-value pairs from non-JSON input
                arguments = {"input": args_str}

        if name:
            tool_calls.append(ToolCall(name=name, arguments=arguments))

    return tool_calls


def _parse_inline_json(text: str) -> List[ToolCall]:
    """Parse inline JSON objects that look like tool calls."""
    tool_calls: List[ToolCall] = []

    # Look for JSON objects in the text
    # Match balanced braces (simple approach - works for most cases)
    json_pattern = r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}"
    matches = re.findall(json_pattern, text)

    for match in matches:
        try:
            data = json.loads(match)
        except json.JSONDecodeError:
            continue

        # Check if this looks like a tool call
        if isinstance(data, dict):
            call = _data_to_tool_call(data)
            if call:
                tool_calls.append(call)

    return tool_calls


def _parse_raw_json_array(text: str) -> List[ToolCall]:
    """Parse a raw JSON array of tool calls."""
    text = text.strip()

    # Try to find a JSON array in the text
    array_pattern = r"\[.*\]"
    match = re.search(array_pattern, text, re.DOTALL)
    if not match:
        return []

    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return []

    if not isinstance(data, list):
        return []

    return _extract_tool_calls_from_data(data)


def _extract_tool_calls_from_data(data: Any) -> List[ToolCall]:
    """Extract tool calls from parsed JSON data (dict or list)."""
    tool_calls: List[ToolCall] = []

    if isinstance(data, dict):
        call = _data_to_tool_call(data)
        if call:
            tool_calls.append(call)
        # Check for nested tool_calls array
        elif "tool_calls" in data and isinstance(data["tool_calls"], list):
            for item in data["tool_calls"]:
                call = _data_to_tool_call(item)
                if call:
                    tool_calls.append(call)
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                call = _data_to_tool_call(item)
                if call:
                    tool_calls.append(call)

    return tool_calls


def _data_to_tool_call(data: Dict[str, Any]) -> Optional[ToolCall]:
    """Convert a dictionary to a ToolCall if it matches expected formats.

    Supports:
    - {"name": "...", "arguments": {...}}
    - {"function": "...", "arguments": {...}}
    - {"tool": "...", "args": {...}}
    - {"tool_call": {"name": "...", "arguments": {...}}}
    - {"function_call": {"name": "...", "arguments": {...}}}
    """
    if not isinstance(data, dict):
        return None

    # Nested tool_call format
    if "tool_call" in data and isinstance(data["tool_call"], dict):
        return _data_to_tool_call(data["tool_call"])

    # Nested function_call format
    if "function_call" in data and isinstance(data["function_call"], dict):
        return _data_to_tool_call(data["function_call"])

    # Direct formats
    name: Optional[str] = None
    arguments: Dict[str, Any] = {}

    # Name extraction
    for key in ("name", "function", "tool", "action"):
        if key in data and isinstance(data[key], str):
            name = data[key]
            break

    if not name:
        return None

    # Arguments extraction
    for key in ("arguments", "args", "parameters", "params", "input", "action_input"):
        if key in data:
            val = data[key]
            if isinstance(val, dict):
                arguments = val
            elif isinstance(val, str):
                try:
                    parsed = json.loads(val)
                    if isinstance(parsed, dict):
                        arguments = parsed
                    else:
                        arguments = {"input": val}
                except json.JSONDecodeError:
                    arguments = {"input": val}
            break

    return ToolCall(name=name, arguments=arguments)
