"""
Code Graph - AST-level function-to-function relationships.

Builds a graph of code dependencies within the workspace:
- Function calls (who calls whom)
- Import dependencies
- Class inheritance
- File-level dependencies
- Complexity metrics per node

Used by agents for:
- Impact analysis (what breaks if I change X?)
- Navigation (find related code)
- Refactoring suggestions
- Test coverage mapping
"""

import ast
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


@dataclass
class CodeNode:
    """A node in the code graph (function, class, module)."""
    id: str
    name: str
    node_type: str  # function, class, module, method
    file_path: str
    line_start: int
    line_end: int
    complexity: int = 0
    docstring: Optional[str] = None
    parameters: List[str] = field(default_factory=list)
    decorators: List[str] = field(default_factory=list)
    calls: List[str] = field(default_factory=list)  # IDs of nodes this calls
    called_by: List[str] = field(default_factory=list)  # IDs of nodes that call this
    imports: List[str] = field(default_factory=list)


@dataclass
class CodeEdge:
    """A relationship between two code nodes."""
    source: str  # Node ID
    target: str  # Node ID
    edge_type: str  # calls, imports, inherits, overrides
    weight: float = 1.0


@dataclass
class ImpactAnalysis:
    """Result of analyzing the impact of changing a node."""
    target_node: str
    directly_affected: List[str] = field(default_factory=list)
    transitively_affected: List[str] = field(default_factory=list)
    test_files_affected: List[str] = field(default_factory=list)
    risk_level: str = "low"  # low, medium, high


class CodeGraphService:
    """Builds and queries the code dependency graph."""

    def __init__(self):
        self._nodes: Dict[str, CodeNode] = {}
        self._edges: List[CodeEdge] = []
        self._file_index: Dict[str, List[str]] = {}  # file → node IDs

    def build_graph(self, workspace_dir: str, extensions: Optional[List[str]] = None):
        """Build the code graph from workspace files."""
        extensions = extensions or [".py"]
        self._nodes.clear()
        self._edges.clear()
        self._file_index.clear()

        workspace = Path(workspace_dir)
        for ext in extensions:
            for file_path in workspace.rglob(f"*{ext}"):
                # Skip common non-source directories
                parts = file_path.parts
                if any(p in parts for p in (".git", "node_modules", "__pycache__", "venv", ".venv")):
                    continue
                self._analyze_file(str(file_path), ext)

        # Build reverse edges (called_by)
        self._build_reverse_edges()

    def _analyze_file(self, file_path: str, extension: str):
        """Analyze a single file and extract nodes."""
        if extension == ".py":
            self._analyze_python_file(file_path)

    def _analyze_python_file(self, file_path: str):
        """Parse a Python file and extract AST information."""
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                source = f.read()

            tree = ast.parse(source, filename=file_path)
        except (SyntaxError, UnicodeDecodeError):
            return

        # Module node
        module_id = f"module:{file_path}"
        module_node = CodeNode(
            id=module_id,
            name=Path(file_path).stem,
            node_type="module",
            file_path=file_path,
            line_start=1,
            line_end=len(source.splitlines()),
        )
        self._nodes[module_id] = module_node
        self._file_index.setdefault(file_path, []).append(module_id)

        # Extract imports
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    module_node.imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    module_node.imports.append(node.module)

        # Extract functions and classes
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                self._extract_function(node, file_path, module_id)
            elif isinstance(node, ast.ClassDef):
                self._extract_class(node, file_path, module_id)

    def _extract_function(self, node: ast.FunctionDef, file_path: str, parent_id: str):
        """Extract a function definition."""
        func_id = f"func:{file_path}:{node.name}:{node.lineno}"
        func_node = CodeNode(
            id=func_id,
            name=node.name,
            node_type="function",
            file_path=file_path,
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            parameters=[arg.arg for arg in node.args.args if arg.arg != "self"],
            decorators=[self._get_decorator_name(d) for d in node.decorator_list],
            docstring=ast.get_docstring(node),
            complexity=self._calculate_complexity(node),
        )

        # Find function calls within this function
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                call_name = self._get_call_name(child)
                if call_name:
                    func_node.calls.append(call_name)

        self._nodes[func_id] = func_node
        self._file_index.setdefault(file_path, []).append(func_id)
        self._edges.append(CodeEdge(source=parent_id, target=func_id, edge_type="contains"))

    def _extract_class(self, node: ast.ClassDef, file_path: str, parent_id: str):
        """Extract a class definition."""
        class_id = f"class:{file_path}:{node.name}:{node.lineno}"
        class_node = CodeNode(
            id=class_id,
            name=node.name,
            node_type="class",
            file_path=file_path,
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            docstring=ast.get_docstring(node),
            decorators=[self._get_decorator_name(d) for d in node.decorator_list],
        )
        self._nodes[class_id] = class_node
        self._file_index.setdefault(file_path, []).append(class_id)

        # Inheritance edges
        for base in node.bases:
            base_name = self._get_call_name(base) if isinstance(base, ast.Call) else getattr(base, "id", None)
            if base_name:
                self._edges.append(CodeEdge(source=class_id, target=f"ref:{base_name}", edge_type="inherits"))

        # Extract methods
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self._extract_function(item, file_path, class_id)

    def _build_reverse_edges(self):
        """Build called_by relationships."""
        # Resolve call references to actual node IDs
        call_map: Dict[str, List[str]] = {}  # name → [node_ids]
        for node_id, node in self._nodes.items():
            call_map.setdefault(node.name, []).append(node_id)

        for node_id, node in self._nodes.items():
            for call_name in node.calls:
                # Find matching nodes
                targets = call_map.get(call_name, [])
                for target_id in targets:
                    if target_id != node_id:
                        self._edges.append(CodeEdge(source=node_id, target=target_id, edge_type="calls"))
                        self._nodes[target_id].called_by.append(node_id)

    def _calculate_complexity(self, node: ast.AST) -> int:
        """Calculate cyclomatic complexity."""
        complexity = 1
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
        return complexity

    def _get_call_name(self, node) -> Optional[str]:
        """Get the name of a function call."""
        if isinstance(node, ast.Call):
            node = node.func
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return node.attr
        return None

    def _get_decorator_name(self, node) -> str:
        """Get decorator name."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Call):
            return self._get_call_name(node) or "unknown"
        elif isinstance(node, ast.Attribute):
            return node.attr
        return "unknown"

    # ─── Query Methods ────────────────────────────────────────────────

    def get_node(self, node_id: str) -> Optional[CodeNode]:
        """Get a specific node."""
        return self._nodes.get(node_id)

    def find_by_name(self, name: str) -> List[CodeNode]:
        """Find nodes by name."""
        return [n for n in self._nodes.values() if n.name == name]

    def get_callers(self, node_id: str) -> List[CodeNode]:
        """Get all nodes that call this node."""
        node = self._nodes.get(node_id)
        if not node:
            return []
        return [self._nodes[cid] for cid in node.called_by if cid in self._nodes]

    def get_callees(self, node_id: str) -> List[CodeNode]:
        """Get all nodes called by this node."""
        return [
            self._nodes[e.target]
            for e in self._edges
            if e.source == node_id and e.edge_type == "calls" and e.target in self._nodes
        ]

    def impact_analysis(self, node_id: str, max_depth: int = 3) -> ImpactAnalysis:
        """Analyze the impact of changing a node."""
        analysis = ImpactAnalysis(target_node=node_id)
        visited: Set[str] = set()

        def traverse(nid: str, depth: int):
            if depth > max_depth or nid in visited:
                return
            visited.add(nid)
            node = self._nodes.get(nid)
            if not node:
                return
            for caller_id in node.called_by:
                if depth == 1:
                    analysis.directly_affected.append(caller_id)
                else:
                    analysis.transitively_affected.append(caller_id)
                traverse(caller_id, depth + 1)

        traverse(node_id, 1)

        # Determine risk
        total_affected = len(analysis.directly_affected) + len(analysis.transitively_affected)
        if total_affected > 20:
            analysis.risk_level = "high"
        elif total_affected > 5:
            analysis.risk_level = "medium"

        return analysis

    def get_graph_data(self) -> Dict[str, Any]:
        """Get full graph data for visualization."""
        return {
            "nodes": [
                {
                    "id": n.id,
                    "name": n.name,
                    "type": n.node_type,
                    "file": n.file_path,
                    "complexity": n.complexity,
                    "lines": n.line_end - n.line_start + 1,
                }
                for n in self._nodes.values()
            ],
            "edges": [
                {"source": e.source, "target": e.target, "type": e.edge_type}
                for e in self._edges
                if e.source in self._nodes and e.target in self._nodes
            ],
            "stats": {
                "total_nodes": len(self._nodes),
                "total_edges": len(self._edges),
                "files": len(self._file_index),
            },
        }


# Singleton
code_graph = CodeGraphService()
