"""Unit tests for the tool call parser.

Tests all 5 parsing formats: JSON code blocks, XML style, ReAct format,
inline JSON, and raw JSON arrays.
"""

import pytest
from agents.tool_parser import parse_tool_calls, ToolCall


class TestJsonCodeBlocks:
    """Test parsing from ```json code blocks."""

    def test_single_tool_call(self):
        text = '```json\n{"name": "file_read", "arguments": {"path": "test.py"}}\n```'
        calls = parse_tool_calls(text)
        assert len(calls) == 1
        assert calls[0].name == "file_read"
        assert calls[0].arguments == {"path": "test.py"}

    def test_multiple_code_blocks(self):
        text = (
            '```json\n{"name": "file_read", "arguments": {"path": "a.py"}}\n```\n'
            'Some text\n'
            '```json\n{"name": "file_write", "arguments": {"path": "b.py", "content": "hi"}}\n```'
        )
        calls = parse_tool_calls(text)
        assert len(calls) == 2
        assert calls[0].name == "file_read"
        assert calls[1].name == "file_write"

    def test_code_block_without_json_marker(self):
        text = '```\n{"name": "shell_exec", "arguments": {"command": "ls"}}\n```'
        calls = parse_tool_calls(text)
        assert len(calls) == 1
        assert calls[0].name == "shell_exec"

    def test_code_block_with_surrounding_text(self):
        text = (
            "I'll list the files for you:\n\n"
            '```json\n{"name": "file_list", "arguments": {"path": "."}}\n```\n\n'
            "This will show the directory contents."
        )
        calls = parse_tool_calls(text)
        assert len(calls) == 1
        assert calls[0].name == "file_list"


class TestXmlStyle:
    """Test parsing XML-style tool calls."""

    def test_tool_call_tags(self):
        text = '<tool_call>{"name": "file_read", "arguments": {"path": "README.md"}}</tool_call>'
        calls = parse_tool_calls(text)
        assert len(calls) == 1
        assert calls[0].name == "file_read"
        assert calls[0].arguments["path"] == "README.md"

    def test_function_call_with_name_attr(self):
        text = '<function_call name="shell_exec">{"command": "ls -la"}</function_call>'
        calls = parse_tool_calls(text)
        assert len(calls) == 1
        assert calls[0].name == "shell_exec"
        assert calls[0].arguments["command"] == "ls -la"

    def test_tool_with_name_attr(self):
        text = '<tool name="grep_search">{"pattern": "TODO", "path": "."}</tool>'
        calls = parse_tool_calls(text)
        assert len(calls) == 1
        assert calls[0].name == "grep_search"

    def test_multiple_xml_calls(self):
        text = (
            '<tool_call>{"name": "file_read", "arguments": {"path": "a.py"}}</tool_call>\n'
            '<tool_call>{"name": "file_read", "arguments": {"path": "b.py"}}</tool_call>'
        )
        calls = parse_tool_calls(text)
        assert len(calls) == 2


class TestReActFormat:
    """Test parsing ReAct-style format."""

    def test_basic_react(self):
        text = (
            "Thought: I need to list files\n"
            "Action: file_list\n"
            'Action Input: {"path": "."}\n'
        )
        calls = parse_tool_calls(text)
        assert len(calls) == 1
        assert calls[0].name == "file_list"
        assert calls[0].arguments == {"path": "."}

    def test_react_with_non_json_input(self):
        text = (
            "Thought: Let me search for this\n"
            "Action: web_search\n"
            "Action Input: python async best practices\n"
        )
        calls = parse_tool_calls(text)
        assert len(calls) == 1
        assert calls[0].name == "web_search"
        assert "input" in calls[0].arguments

    def test_react_with_quoted_action(self):
        text = (
            "Thought: Reading the file\n"
            'Action: "file_read"\n'
            'Action Input: {"path": "config.py"}\n'
        )
        calls = parse_tool_calls(text)
        assert len(calls) == 1
        assert calls[0].name == "file_read"


class TestInlineJson:
    """Test parsing inline JSON objects."""

    def test_inline_tool_call(self):
        text = 'I will use {"name": "file_read", "arguments": {"path": "test.py"}} to read the file.'
        calls = parse_tool_calls(text)
        assert len(calls) == 1
        assert calls[0].name == "file_read"

    def test_function_key(self):
        text = '{"function": "shell_exec", "arguments": {"command": "echo hello"}}'
        calls = parse_tool_calls(text)
        assert len(calls) == 1
        assert calls[0].name == "shell_exec"

    def test_tool_key(self):
        text = '{"tool": "code_exec", "args": {"code": "print(1+1)"}}'
        calls = parse_tool_calls(text)
        assert len(calls) == 1
        assert calls[0].name == "code_exec"


class TestRawJsonArray:
    """Test parsing raw JSON arrays."""

    def test_array_of_tool_calls(self):
        text = '[{"name": "file_read", "arguments": {"path": "a.py"}}, {"name": "file_read", "arguments": {"path": "b.py"}}]'
        calls = parse_tool_calls(text)
        assert len(calls) == 2
        assert calls[0].arguments["path"] == "a.py"
        assert calls[1].arguments["path"] == "b.py"


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_string(self):
        assert parse_tool_calls("") == []

    def test_none_input(self):
        assert parse_tool_calls(None) == []

    def test_whitespace_only(self):
        assert parse_tool_calls("   \n\t  ") == []

    def test_no_tool_calls(self):
        text = "I will just answer your question directly without using any tools."
        assert parse_tool_calls(text) == []

    def test_malformed_json(self):
        text = '```json\n{bad json content}\n```'
        calls = parse_tool_calls(text)
        assert len(calls) == 0

    def test_nested_tool_call_format(self):
        text = '{"tool_call": {"name": "file_read", "arguments": {"path": "x.py"}}}'
        calls = parse_tool_calls(text)
        assert len(calls) == 1
        assert calls[0].name == "file_read"

    def test_arguments_as_string(self):
        text = '{"name": "code_exec", "arguments": "{\\"code\\": \\"print(42)\\"}"}'
        calls = parse_tool_calls(text)
        assert len(calls) == 1
        assert calls[0].name == "code_exec"
