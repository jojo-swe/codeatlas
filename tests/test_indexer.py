from pathlib import Path

from codeatlas.indexer import PythonIndexer


def test_indexes_symbols_and_dependencies(tmp_path: Path) -> None:
    (tmp_path / "sample.py").write_text(
        """
import json

class Base:
    pass

class Worker(Base):
    def run(self):
        return json.dumps({'ok': True})

def helper():
    return Worker().run()
""".strip(),
        encoding="utf-8",
    )

    index = PythonIndexer(tmp_path).index()

    names = {symbol.qualified_name for symbol in index.symbols}
    assert "sample.Base" in names
    assert "sample.Worker" in names
    assert "sample.Worker.run" in names
    assert "sample.helper" in names

    relationships = {(dep.source, dep.target, dep.kind) for dep in index.dependencies}
    assert ("sample.Worker", "Base", "inherits") in relationships
    assert ("sample", "json", "imports") in relationships
    assert ("sample.Worker.run", "json.dumps", "calls") in relationships
    assert not index.errors


def test_ignores_virtual_environment(tmp_path: Path) -> None:
    ignored = tmp_path / ".venv"
    ignored.mkdir()
    (ignored / "noise.py").write_text("def hidden(): pass", encoding="utf-8")

    index = PythonIndexer(tmp_path).index()

    assert index.files == []
    assert index.symbols == []


def test_collects_syntax_errors_without_aborting(tmp_path: Path) -> None:
    (tmp_path / "broken.py").write_text("def broken(:", encoding="utf-8")
    (tmp_path / "valid.py").write_text("def valid(): pass", encoding="utf-8")

    index = PythonIndexer(tmp_path).index()

    assert len(index.errors) == 1
    assert any(symbol.name == "valid" for symbol in index.symbols)
