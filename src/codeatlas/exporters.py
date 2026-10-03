"""Graph exporters for CodeAtlas indexes."""

from __future__ import annotations

import hashlib

from .indexer import CodeIndex


def _node_id(value: str) -> str:
    digest = hashlib.sha1(value.encode("utf-8"), usedforsecurity=False).hexdigest()[:12]
    return f"n_{digest}"


def _escape_label(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def to_mermaid(index: CodeIndex) -> str:
    """Render an index as a deterministic Mermaid flowchart."""

    nodes = {symbol.qualified_name for symbol in index.symbols}
    edges: set[tuple[str, str, str]] = set()
    for dependency in index.dependencies:
        target = dependency.resolved_target or dependency.target
        nodes.add(dependency.source)
        nodes.add(target)
        edges.add((dependency.source, target, dependency.kind))

    lines = ["flowchart LR"]
    for node in sorted(nodes):
        lines.append(f'    {_node_id(node)}["{_escape_label(node)}"]')
    for source, target, kind in sorted(edges):
        lines.append(
            f'    {_node_id(source)} -->|"{_escape_label(kind)}"| {_node_id(target)}'
        )
    return "\n".join(lines)
