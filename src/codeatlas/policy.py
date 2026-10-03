"""Declarative architecture policies for CodeAtlas dependency graphs."""

from __future__ import annotations

import fnmatch
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .analysis import GraphAnalysis


class PolicyError(ValueError):
    """Raised when an architecture policy cannot be loaded or validated."""


@dataclass(slots=True, frozen=True)
class Layer:
    name: str
    patterns: tuple[str, ...]


@dataclass(slots=True, frozen=True)
class Rule:
    source: str
    deny: tuple[str, ...]
    kinds: tuple[str, ...] = ()
    message: str | None = None


@dataclass(slots=True, frozen=True)
class Violation:
    source: str
    target: str
    kind: str
    source_layer: str
    target_layer: str
    message: str


class ArchitecturePolicy:
    """Map indexed symbols into layers and evaluate forbidden graph edges."""

    def __init__(self, layers: list[Layer], rules: list[Rule]) -> None:
        names = [layer.name for layer in layers]
        if not layers:
            raise PolicyError("policy must define at least one layer")
        if len(names) != len(set(names)):
            raise PolicyError("layer names must be unique")
        known = set(names)
        for rule in rules:
            if rule.source not in known:
                raise PolicyError(f"rule references unknown source layer: {rule.source}")
            unknown = set(rule.deny) - known
            if unknown:
                raise PolicyError(f"rule references unknown denied layer: {sorted(unknown)[0]}")
        self.layers = layers
        self.rules = rules

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ArchitecturePolicy":
        raw_layers = payload.get("layers")
        raw_rules = payload.get("rules", [])
        if not isinstance(raw_layers, dict):
            raise PolicyError("'layers' must be an object mapping names to glob patterns")
        if not isinstance(raw_rules, list):
            raise PolicyError("'rules' must be an array")

        layers: list[Layer] = []
        for name, patterns in raw_layers.items():
            if not isinstance(name, str) or not name.strip():
                raise PolicyError("layer names must be non-empty strings")
            if isinstance(patterns, str):
                patterns = [patterns]
            if not isinstance(patterns, list) or not patterns or not all(isinstance(item, str) for item in patterns):
                raise PolicyError(f"layer '{name}' must contain one or more glob patterns")
            layers.append(Layer(name.strip(), tuple(patterns)))

        rules: list[Rule] = []
        for position, item in enumerate(raw_rules, start=1):
            if not isinstance(item, dict):
                raise PolicyError(f"rule {position} must be an object")
            source = item.get("from")
            denied = item.get("deny")
            kinds = item.get("kinds", [])
            message = item.get("message")
            if not isinstance(source, str) or not source:
                raise PolicyError(f"rule {position} requires a non-empty 'from' layer")
            if isinstance(denied, str):
                denied = [denied]
            if not isinstance(denied, list) or not denied or not all(isinstance(value, str) for value in denied):
                raise PolicyError(f"rule {position} requires one or more denied layers")
            if isinstance(kinds, str):
                kinds = [kinds]
            if not isinstance(kinds, list) or not all(isinstance(value, str) for value in kinds):
                raise PolicyError(f"rule {position} 'kinds' must be an array of strings")
            if message is not None and not isinstance(message, str):
                raise PolicyError(f"rule {position} 'message' must be a string")
            rules.append(Rule(source, tuple(denied), tuple(kinds), message))
        return cls(layers, rules)

    @classmethod
    def load(cls, path: str | Path) -> "ArchitecturePolicy":
        policy_path = Path(path)
        try:
            payload = json.loads(policy_path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise PolicyError(f"policy file not found: {policy_path}") from exc
        except json.JSONDecodeError as exc:
            raise PolicyError(f"invalid JSON in {policy_path}: line {exc.lineno}, column {exc.colno}") from exc
        if not isinstance(payload, dict):
            raise PolicyError("policy root must be a JSON object")
        return cls.from_dict(payload)

    def layer_for(self, symbol: str, file: str) -> str | None:
        """Return the first matching layer using symbol or normalized file globs."""
        normalized_file = file.replace("\\", "/")
        for layer in self.layers:
            for pattern in layer.patterns:
                normalized_pattern = pattern.replace("\\", "/")
                if fnmatch.fnmatchcase(symbol, pattern) or fnmatch.fnmatchcase(normalized_file, normalized_pattern):
                    return layer.name
        return None

    def evaluate(self, analysis: GraphAnalysis) -> list[Violation]:
        assignments = {
            name: self.layer_for(name, symbol.file)
            for name, symbol in analysis.symbols.items()
        }
        rules_by_source: dict[str, list[Rule]] = {}
        for rule in self.rules:
            rules_by_source.setdefault(rule.source, []).append(rule)

        violations: list[Violation] = []
        for edge in analysis.edges:
            source_layer = assignments.get(edge.source)
            target_layer = assignments.get(edge.target)
            if source_layer is None or target_layer is None:
                continue
            for rule in rules_by_source.get(source_layer, []):
                if target_layer not in rule.deny:
                    continue
                if rule.kinds and edge.kind not in rule.kinds:
                    continue
                message = rule.message or f"{source_layer} must not depend on {target_layer}"
                violations.append(
                    Violation(
                        source=edge.source,
                        target=edge.target,
                        kind=edge.kind,
                        source_layer=source_layer,
                        target_layer=target_layer,
                        message=message,
                    )
                )
        return sorted(violations, key=lambda item: (item.source, item.target, item.kind, item.message))

    def summary(self, analysis: GraphAnalysis) -> dict[str, Any]:
        assignments: dict[str, str] = {}
        unassigned: list[str] = []
        counts = {layer.name: 0 for layer in self.layers}
        for name, symbol in sorted(analysis.symbols.items()):
            layer = self.layer_for(name, symbol.file)
            if layer is None:
                unassigned.append(name)
            else:
                assignments[name] = layer
                counts[layer] += 1
        violations = self.evaluate(analysis)
        return {
            "layer_counts": counts,
            "assigned_symbol_count": len(assignments),
            "unassigned_symbol_count": len(unassigned),
            "unassigned_symbols": unassigned,
            "violation_count": len(violations),
            "violations": [asdict(item) for item in violations],
        }
