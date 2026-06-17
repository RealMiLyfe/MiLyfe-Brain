"""MCP Schema — Structured tool definitions."""

from typing import Any, Optional
from pydantic import BaseModel, Field


class MCPToolParameter(BaseModel):
    """A parameter for an MCP tool."""
    name: str
    type: str = "string"
    description: str = ""
    required: bool = True
    default: Optional[Any] = None


class MCPToolSchema(BaseModel):
    """Schema for an MCP tool."""
    name: str
    description: str
    parameters: list[MCPToolParameter] = Field(default_factory=list)
    category: str = "general"


class MCPToolCall(BaseModel):
    """An invocation of an MCP tool."""
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    call_id: Optional[str] = None


class MCPToolResult(BaseModel):
    """Result from an MCP tool invocation."""
    call_id: Optional[str] = None
    tool_name: str
    success: bool = True
    result: Any = None
    error: Optional[str] = None
