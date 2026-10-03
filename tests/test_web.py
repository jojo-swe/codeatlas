from __future__ import annotations

from codeatlas.analysis import GraphAnalysis
from codeatlas.indexer import PythonIndexer
from codeatlas.web import build_payload, render_html


def test_build_payload_contains_graph_metrics(tmp_path):
    (tmp_path / "sample.py").write_text(
        "def helper():\n    return 1\n\ndef caller():\n    return helper()\n",
        encoding="utf-8",
    )
    index = PythonIndexer(tmp_path).index()
    analysis = GraphAnalysis(index)

    payload = build_payload(index, analysis)

    ids = {node["id"] for node in payload["nodes"]}
    assert "sample.helper" in ids
    assert "sample.caller" in ids
    assert payload["summary"]["symbol_count"] == 2
    assert payload["analysis"]["resolved_edge_count"] == 1
    assert payload["edges"] == [
        {"source": "sample.caller", "target": "sample.helper", "kind": "calls"}
    ]


def test_payload_marks_cycle_members(tmp_path):
    (tmp_path / "cycle.py").write_text(
        "def first():\n    return second()\n\ndef second():\n    return first()\n",
        encoding="utf-8",
    )
    index = PythonIndexer(tmp_path).index()
    payload = build_payload(index, GraphAnalysis(index))

    cycle_nodes = {node["id"] for node in payload["nodes"] if node["cycle"]}
    assert cycle_nodes == {"cycle.first", "cycle.second"}


def test_render_html_is_self_contained_and_escapes_script_end(tmp_path):
    (tmp_path / "safe.py").write_text("def value():\n    return 1\n", encoding="utf-8")
    index = PythonIndexer(tmp_path).index()
    payload = build_payload(index, GraphAnalysis(index))
    payload["root"] = "</script><script>alert(1)</script>"

    document = render_html(payload)

    assert "<!doctype html>" in document
    assert "CodeAtlas Explorer" in document
    assert "__DATA__" not in document
    assert "</script><script>alert(1)</script>" not in document
    assert "<\\/script>" in document
