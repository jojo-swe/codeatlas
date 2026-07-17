"""Static Python repository indexing for CodeAtlas."""

from __future__ import annotations

import ast
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable


@dataclass(slots=True)
class Symbol:
    """A discovered code symbol."""

    name: str
    kind: str
    file: str
    line: int
    qualified_name: str


@dataclass(slots=True)
class Dependency:
    """A directed relationship between two symbols or modules."""

    source: str
    target: str
    kind: str


@dataclass(slots=True)
class CodeIndex:
    """Serializable result of indexing a repository."""

    root: str
    files: list[str] = field(default_factory=list)
    symbols: list[Symbol] = field(default_factory=list)
    dependencies: list[Dependency] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "root": self.root,
            "files": self.files,
            "symbols": [asdict(symbol) for symbol in self.symbols],
            "dependencies": [asdict(dep) for dep in self.dependencies],
            "errors": self.errors,
            "summary": {
                "file_count": len(self.files),
                "symbol_count": len(self.symbols),
                "dependency_count": len(self.dependencies),
                "error_count": len(self.errors),
            },
        }

    def to_json(self, *, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True)


class _Visitor(ast.NodeVisitor):
    def __init__(self, relative_file: str, module_name: str) -> None:
        self.relative_file = relative_file
        self.module_name = module_name
        self.scope: list[str] = []
        self.symbols: list[Symbol] = []
        self.dependencies: list[Dependency] = []

    def _qualified(self, name: str) -> str:
        parts = [self.module_name, *self.scope, name]
        return ".".join(part for part in parts if part)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        qualified = self._qualified(node.name)
        self.symbols.append(Symbol(node.name, "class", self.relative_file, node.lineno, qualified))
        for base in node.bases:
            target = self._expr_name(base)
            if target:
                self.dependencies.append(Dependency(qualified, target, "inherits"))
        self.scope.append(node.name)
        self.generic_visit(node)
        self.scope.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_function(node, "function" if not self.scope else "method")

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_function(node, "async_function" if not self.scope else "async_method")

    def _visit_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef, kind: str) -> None:
        qualified = self._qualified(node.name)
        self.symbols.append(Symbol(node.name, kind, self.relative_file, node.lineno, qualified))
        self.scope.append(node.name)
        self.generic_visit(node)
        self.scope.pop()

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            self.dependencies.append(Dependency(self.module_name, alias.name, "imports"))

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        module = node.module or ""
        for alias in node.names:
            target = f"{module}.{alias.name}".strip(".")
            self.dependencies.append(Dependency(self.module_name, target, "imports"))

    def visit_Call(self, node: ast.Call) -> None:
        target = self._expr_name(node.func)
        if target:
            source = ".".join([self.module_name, *self.scope]).strip(".") or self.module_name
            self.dependencies.append(Dependency(source, target, "calls"))
        self.generic_visit(node)

    @staticmethod
    def _expr_name(node: ast.AST) -> str | None:
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            parent = _Visitor._expr_name(node.value)
            return f"{parent}.{node.attr}" if parent else node.attr
        return None


class PythonIndexer:
    """Index Python files beneath a repository root without executing them."""

    DEFAULT_IGNORES = {".git", ".venv", "venv", "__pycache__", "build", "dist", ".tox"}

    def __init__(self, root: str | Path, *, ignores: Iterable[str] | None = None) -> None:
        self.root = Path(root).resolve()
        self.ignores = self.DEFAULT_IGNORES | set(ignores or ())

    def index(self) -> CodeIndex:
        if not self.root.exists():
            raise FileNotFoundError(f"Repository path does not exist: {self.root}")
        if not self.root.is_dir():
            raise NotADirectoryError(f"Repository path is not a directory: {self.root}")

        result = CodeIndex(root=str(self.root))
        for path in sorted(self.root.rglob("*.py")):
            relative = path.relative_to(self.root)
            if any(part in self.ignores for part in relative.parts):
                continue

            relative_text = relative.as_posix()
            result.files.append(relative_text)
            module_name = self._module_name(relative)
            try:
                tree = ast.parse(path.read_text(encoding="utf-8"), filename=relative_text)
            except (OSError, UnicodeDecodeError, SyntaxError) as exc:
                result.errors.append(f"{relative_text}: {exc}")
                continue

            visitor = _Visitor(relative_text, module_name)
            visitor.visit(tree)
            result.symbols.extend(visitor.symbols)
            result.dependencies.extend(visitor.dependencies)

        return result

    @staticmethod
    def _module_name(relative: Path) -> str:
        parts = list(relative.with_suffix("").parts)
        if parts and parts[-1] == "__init__":
            parts.pop()
        return ".".join(parts)
