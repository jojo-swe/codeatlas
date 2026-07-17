"""Static Python repository indexing for CodeAtlas."""

from __future__ import annotations

import ast
import json
from collections import defaultdict
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
    resolved_target: str | None = None
    confidence: float = 0.0
    resolution: str | None = None


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
                "resolved_dependency_count": sum(
                    dependency.resolved_target is not None for dependency in self.dependencies
                ),
                "error_count": len(self.errors),
            },
        }

    def to_json(self, *, indent: int | None = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True)


class _Visitor(ast.NodeVisitor):
    def __init__(self, relative_file: str, module_name: str) -> None:
        self.relative_file = relative_file
        self.module_name = module_name
        self.scope: list[str] = []
        self.symbols: list[Symbol] = []
        self.dependencies: list[Dependency] = []
        self.import_aliases: dict[str, str] = {}

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
            local_name = alias.asname or alias.name.split(".")[0]
            self.import_aliases[local_name] = alias.name
            self.dependencies.append(Dependency(self.module_name, alias.name, "imports"))

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        module = node.module or ""
        for alias in node.names:
            target = f"{module}.{alias.name}".strip(".")
            self.import_aliases[alias.asname or alias.name] = target
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
        if isinstance(node, ast.Call):
            return _Visitor._expr_name(node.func)
        return None


class _Resolver:
    """Resolve raw dependency targets against symbols known to the index."""

    def __init__(self, symbols: list[Symbol], import_aliases: dict[str, dict[str, str]]) -> None:
        self.qualified = {symbol.qualified_name for symbol in symbols}
        self.by_suffix: dict[str, list[str]] = defaultdict(list)
        for name in self.qualified:
            parts = name.split(".")
            for width in range(1, min(3, len(parts)) + 1):
                self.by_suffix[".".join(parts[-width:])].append(name)
        self.import_aliases = import_aliases

    def resolve_all(self, dependencies: list[Dependency]) -> None:
        for dependency in dependencies:
            if dependency.kind not in {"calls", "inherits"}:
                continue
            resolved = self._resolve(dependency.source, dependency.target)
            if resolved:
                dependency.resolved_target, dependency.confidence, dependency.resolution = resolved

    def _resolve(self, source: str, target: str) -> tuple[str, float, str] | None:
        module = source.split(".")[0]
        candidates: list[tuple[str, float, str]] = []

        if target in self.qualified:
            candidates.append((target, 1.0, "exact-qualified-name"))

        aliases = self.import_aliases.get(module, {})
        head, separator, tail = target.partition(".")
        if head in aliases:
            expanded = aliases[head] + (f".{tail}" if separator else "")
            if expanded in self.qualified:
                candidates.append((expanded, 0.98, "import-alias"))

        source_parts = source.split(".")
        class_scope = source_parts[:-1] if len(source_parts) >= 3 else source_parts
        if target.startswith("self.") and len(class_scope) >= 2:
            self_target = ".".join([*class_scope, target.removeprefix("self.")])
            if self_target in self.qualified:
                candidates.append((self_target, 0.97, "self-method"))

        local_target = f"{module}.{target}"
        if local_target in self.qualified:
            candidates.append((local_target, 0.95, "same-module"))

        suffix_matches = self.by_suffix.get(target, [])
        local_suffix_matches = [name for name in suffix_matches if name.startswith(f"{module}.")]
        if len(local_suffix_matches) == 1:
            candidates.append((local_suffix_matches[0], 0.9, "unique-local-suffix"))
        elif len(suffix_matches) == 1:
            candidates.append((suffix_matches[0], 0.75, "unique-global-suffix"))

        if not candidates:
            return None
        return max(candidates, key=lambda candidate: candidate[1])


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
        import_aliases: dict[str, dict[str, str]] = {}
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
            import_aliases[module_name] = visitor.import_aliases

        _Resolver(result.symbols, import_aliases).resolve_all(result.dependencies)
        return result

    @staticmethod
    def _module_name(relative: Path) -> str:
        parts = list(relative.with_suffix("").parts)
        if parts and parts[-1] == "__init__":
            parts.pop()
        return ".".join(parts)
