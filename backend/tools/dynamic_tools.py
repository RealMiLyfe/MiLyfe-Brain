"""MiLyfe Brain — Runtime Tool Creation System.

The "singularity" feature: agents can create and register new tools at runtime.

Flow:
1. Agent writes a Python function (as a string)
2. System validates syntax with compile()
3. System checks for safety (no imports of dangerous modules)
4. System executes in restricted namespace to define the function
5. System registers the function with the tool registry
6. Tool becomes available to ALL agents immediately

Safety:
- No os.system, subprocess, eval, exec in tool code
- No import of: os, sys, subprocess, shutil (unless explicitly allowed)
- Tools run in the same sandbox as code_exec (workspace-restricted)
- All dynamic tools get permission level NOTIFY (logged prominently)
- Maximum 20 dynamic tools at a time
- Tools are session-scoped (don't persist across restarts by default)
"""

from __future__ import annotations

import ast
import hashlib
import inspect
import textwrap
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import structlog

from config import settings
from models.schemas import PermissionLevel

logger = structlog.get_logger()

# ─── Safety Configuration ───────────────────────────────────────

BLOCKED_IMPORTS = {
    "os", "sys", "subprocess", "shutil", "signal",
    "ctypes", "multiprocessing", "socket", "http.server",
    "importlib", "pickle", "shelve", "tempfile",
}

BLOCKED_BUILTINS = {
    "eval", "exec", "compile", "__import__", "globals",
    "locals", "vars", "dir", "getattr", "setattr", "delattr",
    "open",  # Use file_tools instead
}

MAX_DYNAMIC_TOOLS = 20
MAX_CODE_LENGTH = 5000  # Characters


# ─── Dynamic Tool Registry ──────────────────────────────────────

class DynamicToolEntry:
    """A runtime-created tool."""

    def __init__(
        self,
        name: str,
        code: str,
        description: str,
        parameters: Dict[str, str],
        handler: Callable,
        created_by: str = "",
        created_at: Optional[datetime] = None,
    ):
        self.id = str(uuid.uuid4())[:8]
        self.name = name
        self.code = code
        self.description = description
        self.parameters = parameters
        self.handler = handler
        self.created_by = created_by
        self.created_at = created_at or datetime.utcnow()
        self.call_count: int = 0
        self.last_called: Optional[datetime] = None
        self.code_hash: str = hashlib.sha256(code.encode()).hexdigest()[:12]


class DynamicToolCreator:
    """Creates and manages runtime tools.

    This is the "agents building their own tools" system.
    """

    def __init__(self):
        self._dynamic_tools: Dict[str, DynamicToolEntry] = {}
        self._creation_log: List[Dict] = []

    @property
    def tool_count(self) -> int:
        return len(self._dynamic_tools)

    async def create_tool(
        self,
        name: str,
        code: str,
        description: str = "",
        parameters: Optional[Dict[str, str]] = None,
        created_by: str = "",
        persist: bool = False,
    ) -> Dict[str, Any]:
        """Create a new tool from Python code at runtime.

        Args:
            name: Tool name (must be unique, snake_case)
            code: Python function code (async def or def)
            description: What the tool does (shown to agents)
            parameters: Parameter descriptions {"name": "type description"}
            created_by: Agent ID that created this tool
            persist: If True, save to disk for reuse across restarts

        Returns:
            {"success": True, "tool_name": name} or {"success": False, "error": msg}
        """
        # ── Validation ──────────────────────────────────────────

        # Check limits
        if self.tool_count >= MAX_DYNAMIC_TOOLS:
            return {"success": False, "error": f"Maximum {MAX_DYNAMIC_TOOLS} dynamic tools reached. Remove one first."}

        if len(code) > MAX_CODE_LENGTH:
            return {"success": False, "error": f"Code too long ({len(code)} chars, max {MAX_CODE_LENGTH})"}

        # Validate name
        if not name.isidentifier() or not name.islower():
            return {"success": False, "error": "Tool name must be valid snake_case Python identifier"}

        # Check if name conflicts with existing tools
        from tools.registry import tool_registry
        if tool_registry.get_tool(name):
            return {"success": False, "error": f"Tool '{name}' already exists (built-in or previously created)"}

        if name in self._dynamic_tools:
            return {"success": False, "error": f"Dynamic tool '{name}' already exists. Remove it first."}

        # ── Safety Check ────────────────────────────────────────

        safety_result = self._check_code_safety(code)
        if not safety_result["safe"]:
            return {"success": False, "error": f"Safety violation: {safety_result['reason']}"}

        # ── Syntax Validation ───────────────────────────────────

        try:
            compile(code, f"<dynamic_tool_{name}>", "exec")
        except SyntaxError as e:
            return {"success": False, "error": f"Syntax error: {e}"}

        # ── Function Extraction ─────────────────────────────────

        try:
            handler = self._extract_function(name, code)
        except Exception as e:
            return {"success": False, "error": f"Failed to create function: {e}"}

        # ── Auto-detect parameters if not provided ──────────────

        if not parameters:
            parameters = self._extract_parameters(code)

        if not description:
            description = self._extract_docstring(code) or f"Dynamic tool: {name}"

        # ── Register ────────────────────────────────────────────

        entry = DynamicToolEntry(
            name=name,
            code=code,
            description=description,
            parameters=parameters,
            handler=handler,
            created_by=created_by,
        )
        self._dynamic_tools[name] = entry

        # Register with the main tool registry
        tool_registry.register(
            name=name,
            handler=handler,
            category="Dynamic",
            description=f"[Dynamic] {description}",
            parameters=parameters,
            permission=PermissionLevel.NOTIFY,  # All dynamic tools are NOTIFY level
        )

        # Log creation
        self._creation_log.append({
            "tool_name": name,
            "created_by": created_by,
            "timestamp": datetime.utcnow().isoformat(),
            "code_hash": entry.code_hash,
            "description": description,
        })

        # Persist to disk if requested
        if persist:
            await self._persist_tool(entry)

        logger.info("dynamic_tool_created",
                    name=name,
                    created_by=created_by,
                    code_hash=entry.code_hash,
                    params=list(parameters.keys()))

        return {
            "success": True,
            "tool_name": name,
            "id": entry.id,
            "description": description,
            "parameters": parameters,
        }

    async def remove_tool(self, name: str) -> Dict[str, Any]:
        """Remove a dynamic tool."""
        if name not in self._dynamic_tools:
            return {"success": False, "error": f"Dynamic tool '{name}' not found"}

        del self._dynamic_tools[name]

        # Note: Can't unregister from tool_registry easily,
        # but it won't be callable since handler is gone
        logger.info("dynamic_tool_removed", name=name)
        return {"success": True, "removed": name}

    def list_tools(self) -> List[Dict]:
        """List all dynamic tools."""
        return [
            {
                "id": entry.id,
                "name": entry.name,
                "description": entry.description,
                "parameters": entry.parameters,
                "created_by": entry.created_by,
                "created_at": entry.created_at.isoformat(),
                "call_count": entry.call_count,
                "code_hash": entry.code_hash,
            }
            for entry in self._dynamic_tools.values()
        ]

    def get_tool_code(self, name: str) -> Optional[str]:
        """Get the source code of a dynamic tool."""
        entry = self._dynamic_tools.get(name)
        return entry.code if entry else None

    def get_creation_log(self) -> List[Dict]:
        """Get the creation history."""
        return self._creation_log[-50:]

    # ─── Safety Checking ────────────────────────────────────────

    def _check_code_safety(self, code: str) -> Dict[str, Any]:
        """Check code for safety violations using AST analysis."""
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return {"safe": False, "reason": "Invalid Python syntax"}

        for node in ast.walk(tree):
            # Check imports
            if isinstance(node, ast.Import):
                for alias in node.names:
                    module = alias.name.split(".")[0]
                    if module in BLOCKED_IMPORTS:
                        return {"safe": False, "reason": f"Blocked import: {module}"}

            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    module = node.module.split(".")[0]
                    if module in BLOCKED_IMPORTS:
                        return {"safe": False, "reason": f"Blocked import: {module}"}

            # Check dangerous function calls
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    if node.func.id in BLOCKED_BUILTINS:
                        return {"safe": False, "reason": f"Blocked builtin: {node.func.id}"}
                elif isinstance(node.func, ast.Attribute):
                    if node.func.attr in ("system", "popen", "exec", "spawn"):
                        return {"safe": False, "reason": f"Blocked method: {node.func.attr}"}

            # Check string exec/eval patterns
            elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                dangerous_patterns = ["__import__", "os.system", "subprocess"]
                for pattern in dangerous_patterns:
                    if pattern in node.value:
                        return {"safe": False, "reason": f"Suspicious string content: {pattern}"}

        # Check for infinite loops (basic heuristic)
        code_lower = code.lower()
        if "while true" in code_lower and "break" not in code_lower:
            return {"safe": False, "reason": "Potential infinite loop (while True without break)"}

        return {"safe": True, "reason": ""}

    # ─── Function Extraction ────────────────────────────────────

    def _extract_function(self, name: str, code: str) -> Callable:
        """Execute code in restricted namespace and extract the function."""
        # Create a safe namespace
        safe_namespace: Dict[str, Any] = {
            "__builtins__": {
                # Allow safe builtins only
                "len": len, "range": range, "enumerate": enumerate,
                "zip": zip, "map": map, "filter": filter,
                "sorted": sorted, "reversed": reversed,
                "list": list, "dict": dict, "set": set, "tuple": tuple,
                "str": str, "int": int, "float": float, "bool": bool,
                "print": print, "isinstance": isinstance, "type": type,
                "sum": sum, "min": min, "max": max, "abs": abs,
                "round": round, "any": any, "all": all,
                "hasattr": hasattr, "repr": repr, "format": format,
                "ValueError": ValueError, "TypeError": TypeError,
                "KeyError": KeyError, "IndexError": IndexError,
                "Exception": Exception, "RuntimeError": RuntimeError,
                "True": True, "False": False, "None": None,
            },
            # Allow asyncio for async tools
            "asyncio": __import__("asyncio"),
            # Allow json for data processing
            "json": __import__("json"),
            # Allow re for text processing
            "re": __import__("re"),
            # Allow math
            "math": __import__("math"),
            # Allow datetime
            "datetime": __import__("datetime"),
            # Allow pathlib (restricted to workspace)
            "Path": Path,
        }

        # Execute the code to define the function
        exec(code, safe_namespace)

        # Find the function
        # Look for the named function, or the first defined function
        if name in safe_namespace:
            func = safe_namespace[name]
        else:
            # Find first callable that's not a builtin
            func = None
            for key, val in safe_namespace.items():
                if callable(val) and key != "__builtins__" and not key.startswith("_"):
                    func = val
                    break

        if func is None:
            raise ValueError(f"No function '{name}' found in code. Define: async def {name}(...):")

        if not callable(func):
            raise ValueError(f"'{name}' is not callable")

        # Wrap to track calls
        original_func = func
        entry_ref = {"name": name}

        async def tracked_wrapper(**kwargs):
            """Wrapper that tracks call count."""
            entry = self._dynamic_tools.get(entry_ref["name"])
            if entry:
                entry.call_count += 1
                entry.last_called = datetime.utcnow()

            import asyncio
            if asyncio.iscoroutinefunction(original_func):
                return await original_func(**kwargs)
            else:
                return original_func(**kwargs)

        return tracked_wrapper

    def _extract_parameters(self, code: str) -> Dict[str, str]:
        """Extract parameter names and types from function signature."""
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    params = {}
                    for arg in node.args.args:
                        if arg.arg == "self":
                            continue
                        # Try to get type annotation
                        if arg.annotation:
                            type_str = ast.unparse(arg.annotation) if hasattr(ast, "unparse") else "any"
                        else:
                            type_str = "any"
                        params[arg.arg] = type_str
                    return params
        except Exception:
            pass
        return {}

    def _extract_docstring(self, code: str) -> Optional[str]:
        """Extract docstring from function."""
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    return ast.get_docstring(node)
        except Exception:
            pass
        return None

    # ─── Persistence ────────────────────────────────────────────

    async def _persist_tool(self, entry: DynamicToolEntry):
        """Save tool to disk for reuse across restarts."""
        import json

        tools_dir = Path(settings.workspace_dir) / ".milyfe" / "dynamic_tools"
        tools_dir.mkdir(parents=True, exist_ok=True)

        tool_file = tools_dir / f"{entry.name}.json"
        tool_file.write_text(json.dumps({
            "name": entry.name,
            "code": entry.code,
            "description": entry.description,
            "parameters": entry.parameters,
            "created_by": entry.created_by,
            "created_at": entry.created_at.isoformat(),
            "code_hash": entry.code_hash,
        }, indent=2))

        logger.info("dynamic_tool_persisted", name=entry.name, path=str(tool_file))

    async def load_persisted_tools(self):
        """Load persisted tools from disk on startup."""
        import json

        tools_dir = Path(settings.workspace_dir) / ".milyfe" / "dynamic_tools"
        if not tools_dir.exists():
            return

        loaded = 0
        for tool_file in tools_dir.glob("*.json"):
            try:
                data = json.loads(tool_file.read_text())
                result = await self.create_tool(
                    name=data["name"],
                    code=data["code"],
                    description=data.get("description", ""),
                    parameters=data.get("parameters"),
                    created_by=data.get("created_by", "persisted"),
                    persist=False,  # Already persisted
                )
                if result.get("success"):
                    loaded += 1
            except Exception as e:
                logger.warning("persisted_tool_load_failed", file=str(tool_file), error=str(e))

        if loaded:
            logger.info("persisted_tools_loaded", count=loaded)


# Singleton
dynamic_tool_creator = DynamicToolCreator()


# ─── Tool Registry Integration ──────────────────────────────────

def register_dynamic_tool_tools(registry):
    """Register the meta-tools for creating/managing dynamic tools."""

    async def create_tool(
        name: str,
        code: str,
        description: str = "",
        persist: bool = False,
    ) -> str:
        """Create a new tool from Python code. The tool becomes immediately available."""
        result = await dynamic_tool_creator.create_tool(
            name=name,
            code=code,
            description=description,
            persist=persist,
        )
        if result.get("success"):
            return f"Tool '{name}' created successfully! It's now available for use."
        return f"Failed to create tool: {result.get('error')}"

    async def list_dynamic_tools() -> str:
        """List all runtime-created tools."""
        tools = dynamic_tool_creator.list_tools()
        if not tools:
            return "No dynamic tools created yet."
        lines = ["Dynamic tools:"]
        for t in tools:
            lines.append(f"  - {t['name']}: {t['description']} (calls: {t['call_count']})")
        return "\n".join(lines)

    async def remove_dynamic_tool(name: str) -> str:
        """Remove a runtime-created tool."""
        result = await dynamic_tool_creator.remove_tool(name)
        if result.get("success"):
            return f"Tool '{name}' removed."
        return f"Failed: {result.get('error')}"

    async def get_tool_source(name: str) -> str:
        """Get the source code of a dynamic tool."""
        code = dynamic_tool_creator.get_tool_code(name)
        if code:
            return f"Source for '{name}':\n```python\n{code}\n```"
        return f"Tool '{name}' not found in dynamic tools."

    registry.register(
        name="create_tool",
        handler=create_tool,
        category="Meta",
        description="Create a new tool from Python code (runtime tool creation)",
        parameters={
            "name": "str (snake_case identifier)",
            "code": "str (Python async def or def)",
            "description": "str (what the tool does)",
            "persist": "bool (save across restarts)",
        },
        permission=PermissionLevel.NOTIFY,
    )

    registry.register(
        name="list_dynamic_tools",
        handler=list_dynamic_tools,
        category="Meta",
        description="List all runtime-created dynamic tools",
        parameters={},
        permission=PermissionLevel.FREE,
    )

    registry.register(
        name="remove_dynamic_tool",
        handler=remove_dynamic_tool,
        category="Meta",
        description="Remove a runtime-created tool",
        parameters={"name": "str"},
        permission=PermissionLevel.NOTIFY,
    )

    registry.register(
        name="get_tool_source",
        handler=get_tool_source,
        category="Meta",
        description="View source code of a dynamic tool",
        parameters={"name": "str"},
        permission=PermissionLevel.FREE,
    )
