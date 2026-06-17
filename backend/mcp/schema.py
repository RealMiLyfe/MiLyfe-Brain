"""MiLyfe Brain — MCP Schema Definitions."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class MCPParameter(BaseModel):
    name: str
    type: str = "string"
    description: str = ""
    required: bool = False
    default: Any = None


class MCPToolSchema(BaseModel):
    name: str
    description: str
    parameters: List[MCPParameter] = []
    returns: str = "string"


class MCPToolCall(BaseModel):
    tool_name: str
    arguments: Dict[str, Any] = {}
    request_id: Optional[str] = None


class MCPToolResult(BaseModel):
    request_id: Optional[str] = None
    success: bool
    output: Any = None
    error: Optional[str] = None


class MCPCapabilities(BaseModel):
    tools: List[MCPToolSchema] = []
    version: str = "1.0"
    name: str = "milyfe-brain"
