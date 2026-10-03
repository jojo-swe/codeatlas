from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from codeatlas.git_history import GitHistoryAnalysis, GitHistoryError


def git(root: Path, *args: str, env: dict[str, str] | None = None) -> None:
    subprocess.run(["git", "-C", str(root), *args], check=True, env=env, capture_output=True)


def commit(root: Path, message: str, *, name: str, email: str) -> None:
    git(root, "add", ".")
    git(
        root,
        "-c",
        f"user.name={name}",
        "-c",
        f"user.email={email}",
        "commit",
        "-m",
        message,
    )


def test_git_history_ranks_churn_ownership_and_coupling(tmp_path: Path) -> None:
    git(tmp_path, "init")
    (tmp_path / "a.py").write_text("a = 1\n", encoding="utf-8")
    (tmp_path / "b.py").write_text("b = 1\n", encoding="utf-8")
    commit(tmp_path, "initial", name="Alice", email="alice@example.com")

    (tmp_path / "a.py").write_text("a = 2\nmore = True\n", encoding="utf-8")
    (tmp_path / "b.py").write_text("b = 2\n", encoding="utf-8")
    commit(tmp_path, "change together", name="Alice", email="alice@example.com")

    (tmp_path / "a.py").write_text("a = 3\nmore = True\n", encoding="utf-8")
    (tmp_path / "b.py").write_text("b = 3\n", encoding="utf-8")
    commit(tmp_path, "change together again", name="Bob", email="bob@example.com")

    analysis = GitHistoryAnalysis(tmp_path, since=None)
    summary = analysis.summary()

    assert summary["commit_count"] == 3
    assert summary["author_count"] == 2
    files = {item["file"]: item for item in summary["files"]}
    assert files["a.py"]["commits"] == 3
    assert files["a.py"]["churn"] > 0
    assert files["a.py"]["primary_author"].startswith("Alice")
    assert files["a.py"]["bus_factor"] == 1
    assert summary["couplings"][0]["left"] == "a.py"
    assert summary["couplings"][0]["right"] == "b.py"
    assert summary["couplings"][0]["commits"] == 3
    assert summary["couplings"][0]["confidence"] == 1.0


def test_git_history_rejects_non_repository(tmp_path: Path) -> None:
    with pytest.raises(GitHistoryError):
        GitHistoryAnalysis(tmp_path)
