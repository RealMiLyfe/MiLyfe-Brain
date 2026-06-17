"""
MiLyfe Brain - Dynamic Tool Creation

Runtime tool creation with AST safety analysis.
"""
from __future__ import annotations

import ast
import inspect
import io
import traceback
from contextlib import redirect_stdout, redirect_stderr
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, TYPE_CHECKING

from models.schemas import PermissionLevel

if TYPE_CHECKING:
    from tools.registry import ToolRegistry

BLOCKED_IMPORTS = {"os", "sys", "subprocess", "shutil", "signal", "ctypes", "socket"}
BLOCKED_BUILTINS = {"eval", "exec", "compile", "__import__", "globals", "open"}
MAX_DYNAMIC_TOOLS = 20
MAX_CODE_LENGTH = 5000


class DynamicToolCreator:
    """Singleton for creating and managing dynamic tools at runtime."""

    _instance: Optional[DynamicToolCreator] = None
    _tools: Dict[str, Dict[str, Any]]
    _registry: Optional[ToolRegistry]

    def __new__(cls) -> DynamicToolCreator:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._tools = {}
            cls._instance._registry = None
        return cls._instance

    def set_registry(self, registry: ToolRegistry) -> None:
        """Set the tool registry reference."""
        self._registry = registry

    def create_tool(
        self,
        name: str,
        code: str,
        description: str,
        parameters: Optional[Dict[str, Any]] = None,
        created_by: str = "agent",
        persist: bool = False,
    ) -> Dict[str, Any]:
        """Create a new dynamic tool from code.

        Args:
            name: Tool name (must be unique, alphanumeric + underscore).
            code: Python function code defining the tool.
            description: Tool description.
            parameters: Parameter schema dict.
            created_by: Who created this tool.
            persist: Whether to save to disk (future use).

        Returns:
            Dict with success status and tool info.
        """
        # Validate name
        if not name.isidentifier():
            return {"success": False, "error": f"Invalid tool name: '{name}' (must be valid Python identifier)"}

        if name.startswith("_"):
            return {"success": False, "error": "Tool name cannot start with underscore"}

        # Check limits
        if len(self._tools) >= MAX_DYNAMIC_TOOLS:
            return {"success": False, "error": f"Maximum {MAX_DYNAMIC_TOOLS} dynamic tools reached"}

        if len(code) > MAX_CODE_LENGTH:
            return {"success": False, "error": f"Code exceeds maximum length ({MAX_CODE_LENGTH} chars)"}

        # Check if name conflicts with existing tools
        if self._registry and self._registry.get_tool(name) is not None:
            if name not in self._tools:
                return {"success": False, "error": f"Tool '{name}' already exists as a built-in tool"}

        # Safety check
        safety = self._check_code_safety(code)
        if not safety["safe"]:
            return {"success": False, "error": f"Code safety check failed: {safety['reason']}"}

        # Extract function
        try:
            handler = self._extract_function(name, code)
        except Exception as e:
            return {"success": False, "error": f"Failed to extract function: {e}"}

        # Extract parameters if not provided
        if parameters is None:
            parameters = self._extract_parameters(code)

        # Store dynamic tool
        self._tools[name] = {
            "name": name,
            "code": code,
            "description": description,
            "parameters": parameters or {},
            "handler": handler,
            "created_by": created_by,
            "created_at": datetime.utcnow().isoformat(),
            "persist": persist,
        }

        # Register with tool registry
        if self._registry:
            self._registry.register(
                name=name,
                handler=handler,
                category="dynamic",
                description=f"[Dynamic] {description}",
                parameters=parameters or {},
                permission=PermissionLevel.MODERATE,
                returns="Dynamic tool output",
            )

        return {
            "success": True,
            "tool_name": name,
            "message": f"Dynamic tool '{name}' created successfully",
        }

    def remove_tool(self, name: str) -> Dict[str, Any]:
        """Remove a dynamic tool.

        Args:
            name: Tool name to remove.

        Returns:
            Dict with success status.
        """
        if name not in self._tools:
            return {"success": False, "error": f"Dynamic tool '{name}' not found"}

        del self._tools[name]

        # Remove from registry
        if self._registry and name in self._registry._tools:
            del self._registry._tools[name]

        return {"success": True, "message": f"Dynamic tool '{name}' removed"}

    def list_tools(self) -> List[Dict[str, Any]]:
        """List all dynamic tools.

        Returns:
            List of tool info dicts.
        """
        return [
            {
                "name": t["name"],
                "description": t["description"],
                "created_by": t["created_by"],
                "created_at": t["created_at"],
                "parameters": t["parameters"],
            }
            for t in self._tools.values()
        ]

    def get_tool_code(self, name: str) -> Optional[str]:
        """Get the source code of a dynamic tool.

        Args:
            name: Tool name.

        Returns:
            Source code or None if not found.
        """
        if name in self._tools:
            return self._tools[name]["code"]
        return None

    def _check_code_safety(self, code: str) -> Dict[str, Any]:
        """Analyze code using AST for safety issues.

        Args:
            code: Python source code.

        Returns:
            Dict with 'safe' bool and 'reason' if unsafe.
        """
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return {"safe": False, "reason": f"Syntax error: {e}"}

        for node in ast.walk(tree):
            # Check for blocked imports
            if isinstance(node, ast.Import):
                for alias in node.names:
                    module_root = alias.name.split(".")[0]
                    if module_root in BLOCKED_IMPORTS:
                        return {"safe": False, "reason": f"Blocked import: {alias.name}"}

            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    module_root = node.module.split(".")[0]
                    if module_root in BLOCKED_IMPORTS:
                        return {"safe": False, "reason": f"Blocked import: {node.module}"}

            # Check for blocked builtins in calls
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    if node.func.id in BLOCKED_BUILTINS:
                        return {"safe": False, "reason": f"Blocked builtin: {node.func.id}"}
                elif isinstance(node.func, ast.Attribute):
                    if node.func.attr in BLOCKED_BUILTINS:
                        return {"safe": False, "reason": f"Blocked call: .{node.func.attr}()"}

            # Check for attribute access to dunder methods (except __init__, __str__, __repr__)
            elif isinstance(node, ast.Attribute):
                allowed_dunders = {"__init__", "__str__", "__repr__", "__len__", "__iter__", "__next__", "__enter__", "__exit__"}
                if node.attr.startswith("__") and node.attr.endswith("__"):
                    if node.attr not in allowed_dunders:
                        return {"safe": False, "reason": f"Blocked dunder access: {node.attr}"}

        return {"safe": True}

    def _extract_function(self, name: str, code: str) -> Callable[..., Any]:
        """Extract a callable function from code.

        Args:
            name: Expected function name.
            code: Python source code.

        Returns:
            Extracted callable.
        """
        namespace: Dict[str, Any] = {"__builtins__": __builtins__}

        exec(compile(code, f"<dynamic:{name}>", "exec"), namespace)  # noqa: S102

        if name in namespace and callable(namespace[name]):
            return namespace[name]

        # Look for first function defined
        for key, value in namespace.items():
            if callable(value) and not key.startswith("_") and key != "__builtins__":
                return value

        raise ValueError(f"No callable function '{name}' found in code")

    def _extract_parameters(self, code: str) -> Dict[str, Any]:
        """Extract parameter schema from function code using AST.

        Args:
            code: Python source code.

        Returns:
            Parameter schema dict.
        """
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return {}

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                params: Dict[str, Any] = {}
                args = node.args

                # Positional and keyword args
                all_args = args.args + args.kwonlyargs
                defaults = args.defaults + args.kw_defaults

                # Pad defaults to align with args
                num_no_default = len(args.args) - len(args.defaults)
                padded_defaults = [None] * num_no_default + list(args.defaults)

                for i, arg in enumerate(args.args):
                    if arg.arg == "self":
                        continue
                    param_info: Dict[str, Any] = {"type": "string"}

                    # Check annotation
                    if arg.annotation:
                        if isinstance(arg.annotation, ast.Name):
                            type_map = {"int": "integer", "float": "number", "bool": "boolean", "str": "string", "list": "array", "dict": "object"}
                            param_info["type"] = type_map.get(arg.annotation.id, "string")

                    # Check default value
                    if i < len(padded_defaults) and padded_defaults[i] is not None:
                        default_node = padded_defaults[i]
                        if isinstance(default_node, ast.Constant):
                            param_info["default"] = default_node.value
                    else:
                        param_info["required"] = True

                    params[arg.arg] = param_info

                return params

        return {}


# Singleton instance
dynamic_tool_creator = DynamicToolCreator()


# ============================================================
# Tool handler wrappers for registry
# ============================================================


def _create_tool_handler(
    name: str,
    code: str,
    description: str,
    parameters: str = "",
    created_by: str = "agent",
    persist: bool = False,
) -> str:
    """Create a new dynamic tool. Handler for registry."""
    import json as _json

    params = None
    if parameters:
        try:
            params = _json.loads(parameters)
        except _json.JSONDecodeError:
            return "Error: 'parameters' must be valid JSON"

    result = dynamic_tool_creator.create_tool(
        name=name,
        code=code,
        description=description,
        parameters=params,
        created_by=created_by,
        persist=persist,
    )

    if result["success"]:
        return result["message"]
    return f"Error: {result['error']}"


def _list_dynamic_tools_handler() -> str:
    """List all dynamic tools. Handler for registry."""
    tools = dynamic_tool_creator.list_tools()
    if not tools:
        return "No dynamic tools created"

    lines = [f"Dynamic tools ({len(tools)}):"]
    for t in tools:
        lines.append(f"  - {t['name']}: {t['description']} (by {t['created_by']}, {t['created_at']})")
    return "\n".join(lines)


def _remove_dynamic_tool_handler(name: str) -> str:
    """Remove a dynamic tool. Handler for registry."""
    result = dynamic_tool_creator.remove_tool(name)
    if result["success"]:
        return result["message"]
    return f"Error: {result['error']}"


def _get_tool_source_handler(name: str) -> str:
    """Get source code of a dynamic tool. Handler for registry."""
    code = dynamic_tool_creator.get_tool_code(name)
    if code is None:
        return f"Error: Dynamic tool '{name}' not found"
    return f"Source code for '{name}':\n\n{code}"


def register_dynamic_tool_tools(registry: ToolRegistry) -> None:
    """Register dynamic tool management tools with the registry."""
    dynamic_tool_creator.set_registry(registry)

    registry.register(
        name="create_tool",
        handler=_create_tool_handler,
        category="dynamic",
        description="Create a new dynamic tool from Python code at runtime.",
        parameters={
            "name": {"type": "string", "description": "Tool name (valid Python identifier)", "required": True},
            "code": {"type": "string", "description": "Python function code", "required": True},
            "description": {"type": "string", "description": "Tool description", "required": True},
            "parameters": {"type": "string", "description": "Parameter schema as JSON string", "default": ""},
            "created_by": {"type": "string", "description": "Creator identifier", "default": "agent"},
            "persist": {"type": "boolean", "description": "Whether to persist to disk", "default": False},
        },
        permission=PermissionLevel.MODERATE,
        returns="Success message or error",
    )

    registry.register(
        name="list_dynamic_tools",
        handler=_list_dynamic_tools_handler,
        category="dynamic",
        description="List all dynamically created tools.",
        parameters={},
        permission=PermissionLevel.SAFE,
        returns="Formatted list of dynamic tools",
    )

    registry.register(
        name="remove_dynamic_tool",
        handler=_remove_dynamic_tool_handler,
        category="dynamic",
        description="Remove a dynamically created tool.",
        parameters={
            "name": {"type": "string", "description": "Tool name to remove", "required": True},
        },
        permission=PermissionLevel.MODERATE,
        returns="Success or error message",
    )

    registry.register(
        name="get_tool_source",
        handler=_get_tool_source_handler,
        category="dynamic",
        description="Get the source code of a dynamic tool.",
        parameters={
            "name": {"type": "string", "description": "Dynamic tool name", "required": True},
        },
        permission=PermissionLevel.SAFE,
        returns="Source code of the dynamic tool",
    )
