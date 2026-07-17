from pathlib import Path

from codeatlas.exporters import to_mermaid
from codeatlas.indexer import PythonIndexer


def test_resolves_local_constructor_method_and_self_calls(tmp_path: Path) -> None:
    (tmp_path / "sample.py").write_text(
        """
class Worker:
    def run(self):
        return self.finish()

    def finish(self):
        return True

def helper():
    return Worker().run()
""".strip(),
        encoding="utf-8",
    )

    index = PythonIndexer(tmp_path).index()
    calls = {
        dependency.target: dependency
        for dependency in index.dependencies
        if dependency.kind == "calls"
    }

    assert calls["self.finish"].resolved_target == "sample.Worker.finish"
    assert calls["self.finish"].confidence == 0.97
    assert calls["Worker.run"].resolved_target == "sample.Worker.run"
    assert calls["Worker.run"].resolution == "same-module"


def test_resolves_import_alias_to_known_symbol(tmp_path: Path) -> None:
    (tmp_path / "service.py").write_text("def execute(): return True", encoding="utf-8")
    (tmp_path / "app.py").write_text(
        "from service import execute as run\n\ndef main():\n    return run()\n",
        encoding="utf-8",
    )

    index = PythonIndexer(tmp_path).index()
    call = next(dependency for dependency in index.dependencies if dependency.kind == "calls")

    assert call.target == "run"
    assert call.resolved_target == "service.execute"
    assert call.resolution == "import-alias"


def test_mermaid_export_is_deterministic_and_uses_resolved_targets(tmp_path: Path) -> None:
    (tmp_path / "sample.py").write_text(
        "class Worker:\n    def run(self): pass\n\ndef main():\n    Worker().run()\n",
        encoding="utf-8",
    )

    index = PythonIndexer(tmp_path).index()
    first = to_mermaid(index)
    second = to_mermaid(index)

    assert first == second
    assert first.startswith("flowchart LR\n")
    assert '"sample.Worker.run"' in first
    assert '"calls"' in first
