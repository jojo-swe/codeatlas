import json

import pytest

from codeatlas.analysis import GraphAnalysis
from codeatlas.indexer import CodeIndex, Dependency, Symbol
from codeatlas.policy import ArchitecturePolicy, PolicyError


def sample_analysis() -> GraphAnalysis:
    index = CodeIndex(
        root="/repo",
        files=["app/ui/view.py", "app/service/orders.py", "app/db/store.py"],
        symbols=[
            Symbol("render", "function", "app/ui/view.py", 1, "app.ui.view.render"),
            Symbol("place_order", "function", "app/service/orders.py", 1, "app.service.orders.place_order"),
            Symbol("save", "function", "app/db/store.py", 1, "app.db.store.save"),
        ],
        dependencies=[
            Dependency("app.ui.view.render", "app.service.orders.place_order", "calls"),
            Dependency("app.ui.view.render", "app.db.store.save", "calls"),
            Dependency("app.service.orders.place_order", "app.db.store.save", "calls"),
        ],
    )
    return GraphAnalysis(index)


def sample_policy() -> ArchitecturePolicy:
    return ArchitecturePolicy.from_dict(
        {
            "layers": {
                "ui": ["app.ui.*", "app/ui/**"],
                "service": "app.service.*",
                "database": "app.db.*",
            },
            "rules": [
                {
                    "from": "ui",
                    "deny": ["database"],
                    "kinds": ["calls"],
                    "message": "UI must call services instead of the database",
                }
            ],
        }
    )


def test_detects_forbidden_cross_layer_dependency() -> None:
    summary = sample_policy().summary(sample_analysis())
    assert summary["layer_counts"] == {"ui": 1, "service": 1, "database": 1}
    assert summary["violation_count"] == 1
    assert summary["violations"][0] == {
        "source": "app.ui.view.render",
        "target": "app.db.store.save",
        "kind": "calls",
        "source_layer": "ui",
        "target_layer": "database",
        "message": "UI must call services instead of the database",
    }


def test_rule_can_be_limited_to_dependency_kinds() -> None:
    policy = ArchitecturePolicy.from_dict(
        {
            "layers": {"ui": "app.ui.*", "database": "app.db.*", "service": "app.service.*"},
            "rules": [{"from": "ui", "deny": "database", "kinds": ["inherits"]}],
        }
    )
    assert policy.evaluate(sample_analysis()) == []


def test_file_globs_assign_symbols_when_symbol_glob_does_not() -> None:
    policy = ArchitecturePolicy.from_dict(
        {
            "layers": {"presentation": "app/ui/**", "other": "app/service/**"},
            "rules": [],
        }
    )
    summary = policy.summary(sample_analysis())
    assert summary["layer_counts"]["presentation"] == 1
    assert summary["unassigned_symbol_count"] == 1


def test_loads_policy_from_json_file(tmp_path) -> None:
    path = tmp_path / "codeatlas.policy.json"
    path.write_text(
        json.dumps({"layers": {"all": "app.*"}, "rules": []}),
        encoding="utf-8",
    )
    policy = ArchitecturePolicy.load(path)
    assert policy.summary(sample_analysis())["assigned_symbol_count"] == 3


@pytest.mark.parametrize(
    "payload, message",
    [
        ({"rules": []}, "'layers' must be an object"),
        ({"layers": {}}, "at least one layer"),
        ({"layers": {"ui": "app.ui.*"}, "rules": [{"from": "missing", "deny": "ui"}]}, "unknown source layer"),
        ({"layers": {"ui": "app.ui.*"}, "rules": [{"from": "ui", "deny": "missing"}]}, "unknown denied layer"),
    ],
)
def test_rejects_invalid_policies(payload, message) -> None:
    with pytest.raises(PolicyError, match=message):
        ArchitecturePolicy.from_dict(payload)
