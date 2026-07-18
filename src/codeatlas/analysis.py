"""Graph intelligence for CodeAtlas indexes."""

from __future__ import annotations

from collections import Counter, defaultdict, deque
from dataclasses import asdict, dataclass

from .indexer import CodeIndex


@dataclass(slots=True, frozen=True)
class Hotspot:
    """A symbol ranked by structural risk and graph centrality."""

    symbol: str
    file: str
    kind: str
    inbound: int
    outbound: int
    fan_total: int
    risk_score: float


@dataclass(slots=True, frozen=True)
class Cycle:
    """A strongly connected dependency cycle."""

    members: tuple[str, ...]


class GraphAnalysis:
    """Derived graph metrics, cycles, reachability and export helpers."""

    def __init__(self, index: CodeIndex) -> None:
        self.index = index
        self.symbols = {symbol.qualified_name: symbol for symbol in index.symbols}
        self.edges = [
            dep
            for dep in index.dependencies
            if dep.source in self.symbols and dep.target in self.symbols
        ]
        self.forward: dict[str, set[str]] = defaultdict(set)
        self.reverse: dict[str, set[str]] = defaultdict(set)
        for edge in self.edges:
            self.forward[edge.source].add(edge.target)
            self.reverse[edge.target].add(edge.source)

    def hotspots(self, *, limit: int = 20) -> list[Hotspot]:
        ranked: list[Hotspot] = []
        for name, symbol in self.symbols.items():
            inbound = len(self.reverse[name])
            outbound = len(self.forward[name])
            fan_total = inbound + outbound
            kind_weight = 1.25 if "method" in symbol.kind else 1.0
            risk = round((inbound * 2.0 + outbound * 1.25 + fan_total**1.35) * kind_weight, 2)
            ranked.append(
                Hotspot(
                    symbol=name,
                    file=symbol.file,
                    kind=symbol.kind,
                    inbound=inbound,
                    outbound=outbound,
                    fan_total=fan_total,
                    risk_score=risk,
                )
            )
        return sorted(ranked, key=lambda item: (-item.risk_score, item.symbol))[: max(limit, 0)]

    def cycles(self) -> list[Cycle]:
        """Return dependency cycles using Tarjan strongly connected components."""
        index = 0
        stack: list[str] = []
        on_stack: set[str] = set()
        indices: dict[str, int] = {}
        lowlink: dict[str, int] = {}
        components: list[Cycle] = []

        def visit(node: str) -> None:
            nonlocal index
            indices[node] = index
            lowlink[node] = index
            index += 1
            stack.append(node)
            on_stack.add(node)

            for target in sorted(self.forward[node]):
                if target not in indices:
                    visit(target)
                    lowlink[node] = min(lowlink[node], lowlink[target])
                elif target in on_stack:
                    lowlink[node] = min(lowlink[node], indices[target])

            if lowlink[node] != indices[node]:
                return
            members: list[str] = []
            while True:
                member = stack.pop()
                on_stack.remove(member)
                members.append(member)
                if member == node:
                    break
            if len(members) > 1 or node in self.forward[node]:
                components.append(Cycle(tuple(sorted(members))))

        for node in sorted(self.symbols):
            if node not in indices:
                visit(node)
        return sorted(components, key=lambda cycle: cycle.members)

    def impact(self, symbol: str, *, depth: int | None = None) -> list[str]:
        """Return transitive callers affected by a change to ``symbol``."""
        if symbol not in self.symbols:
            raise KeyError(symbol)
        seen = {symbol}
        queue = deque([(symbol, 0)])
        impacted: list[str] = []
        while queue:
            current, level = queue.popleft()
            if depth is not None and level >= depth:
                continue
            for caller in sorted(self.reverse[current]):
                if caller in seen:
                    continue
                seen.add(caller)
                impacted.append(caller)
                queue.append((caller, level + 1))
        return impacted

    def summary(self) -> dict[str, object]:
        hotspot_data = [asdict(item) for item in self.hotspots()]
        cycle_data = [list(cycle.members) for cycle in self.cycles()]
        kinds = Counter(symbol.kind for symbol in self.index.symbols)
        files = Counter(symbol.file for symbol in self.index.symbols)
        return {
            "hotspots": hotspot_data,
            "cycles": cycle_data,
            "symbol_kinds": dict(sorted(kinds.items())),
            "symbols_per_file": dict(sorted(files.items())),
            "resolved_edge_count": len(self.edges),
            "unresolved_edge_count": len(self.index.dependencies) - len(self.edges),
        }

    def to_mermaid(self) -> str:
        lines = ["flowchart LR"]
        ids = {name: f"n{position}" for position, name in enumerate(sorted(self.symbols))}
        for name in sorted(self.symbols):
            label = name.replace('"', "'")
            lines.append(f'  {ids[name]}["{label}"]')
        for edge in sorted(self.edges, key=lambda dep: (dep.source, dep.target, dep.kind)):
            lines.append(f"  {ids[edge.source]} -->|{edge.kind}| {ids[edge.target]}")
        return "\n".join(lines) + "\n"
