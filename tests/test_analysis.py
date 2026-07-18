from codeatlas.analysis import GraphAnalysis
from codeatlas.indexer import CodeIndex, Dependency, Symbol


def sample_index() -> CodeIndex:
    return CodeIndex(
        root="/repo",
        files=["app.py"],
        symbols=[
            Symbol("a", "function", "app.py", 1, "app.a"),
            Symbol("b", "function", "app.py", 4, "app.b"),
            Symbol("c", "function", "app.py", 7, "app.c"),
            Symbol("orphan", "function", "app.py", 10, "app.orphan"),
        ],
        dependencies=[
            Dependency("app.a", "app.b", "calls"),
            Dependency("app.b", "app.c", "calls"),
            Dependency("app.c", "app.a", "calls"),
            Dependency("app.a", "external.print", "calls"),
        ],
    )


def test_detects_cycles_and_unresolved_edges() -> None:
    analysis = GraphAnalysis(sample_index())
    assert [cycle.members for cycle in analysis.cycles()] == [("app.a", "app.b", "app.c")]
    assert analysis.summary()["resolved_edge_count"] == 3
    assert analysis.summary()["unresolved_edge_count"] == 1


def test_impact_walks_transitive_callers_without_looping() -> None:
    analysis = GraphAnalysis(sample_index())
    assert analysis.impact("app.c") == ["app.b", "app.a"]
    assert analysis.impact("app.c", depth=1) == ["app.b"]


def test_hotspots_are_ranked_deterministically() -> None:
    hotspots = GraphAnalysis(sample_index()).hotspots()
    assert hotspots[0].symbol == "app.a"
    assert hotspots[-1].symbol == "app.orphan"
    assert hotspots[0].risk_score > hotspots[-1].risk_score


def test_mermaid_contains_resolved_nodes_and_edges_only() -> None:
    diagram = GraphAnalysis(sample_index()).to_mermaid()
    assert diagram.startswith("flowchart LR\n")
    assert "external.print" not in diagram
    assert "-->|calls|" in diagram
