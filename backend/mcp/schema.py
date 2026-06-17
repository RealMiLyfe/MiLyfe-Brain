"""MiLyfe Brain — MCP Schema Types.

Dataclasses representing MCP (Model Context Protocol) tool definitions,
invocations, and results.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class MCPToolParameter:
    """Describes a single parameter of an MCP tool."""

    name: str
    type: str  # e.g., "string", "integer", "boolean", "object", "array"
    description: str = ""
    required: bool = False
    default: Any = None


@dataclass
class MCPToolSchema:
    """Schema definition for an MCP-compatible tool.

    Describes the tool's name, purpose, and expected parameters
    in a format compatible with the Model Context Protocol.
    """

    name: str
    description: str
    parameters: List[MCPToolParameter] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to a JSON-compatible dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    p.name: {
                        "type": p.type,
                        "description": p.description,
                        **({"default": p.default} if p.default is not None else {}),
                    }
                    for p in self.parameters
                },
                "required": [p.name for p in self.parameters if p.required],
            },
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> MCPToolSchema:
        """Deserialize from a JSON-compatible dictionary."""
        params = []
        param_props = data.get("parameters", {}).get("properties", {})
        required_params = data.get("parameters", {}).get("required", [])

        for name, prop in param_props.items():
            params.append(
                MCPToolParameter(
                    name=name,
                    type=prop.get("type", "string"),
                    description=prop.get("description", ""),
                    required=name in required_params,
                    default=prop.get("default"),
                )
            )

        return cls(
            name=data["name"],
            description=data.get("description", ""),
            parameters=params,
        )


@dataclass
class MCPToolCall:
    """Represents an invocation request for an MCP tool.

    Contains the tool name and the arguments to pass.
    """

    name: str
    arguments: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to a JSON-compatible dictionary."""
        return {
            "name": self.name,
            "arguments": self.arguments,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> MCPToolCall:
        """Deserialize from a JSON-compatible dictionary."""
        return cls(
            name=data["name"],
            arguments=data.get("arguments", {}),
        )


@dataclass
class MCPToolResult:
    """Represents the result of an MCP tool invocation.

    Contains either a successful result or an error message.
    """

    name: str
    result: Any = None
    error: Optional[str] = None

    @property
    def success(self) -> bool:
        """Whether the tool call completed successfully."""
        return self.error is None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to a JSON-compatible dictionary."""
        data: Dict[str, Any] = {"name": self.name}
        if self.error is not None:
            data["error"] = self.error
        else:
            data["result"] = self.result
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> MCPToolResult:
        """Deserialize from a JSON-compatible dictionary."""
        return cls(
            name=data["name"],
            result=data.get("result"),
            error=data.get("error"),
        )
