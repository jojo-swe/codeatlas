"""Git-history intelligence for CodeAtlas.

The analyzer shells out to the local ``git`` executable and never contacts a
remote. It is deliberately dependency-free and degrades cleanly when a target
is not a Git worktree.
"""

from __future__ import annotations

import math
import subprocess
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from itertools import combinations
from pathlib import Path
from typing import Any

from .analysis import GraphAnalysis


class GitHistoryError(RuntimeError):
    """Raised when Git history cannot be inspected."""


@dataclass(slots=True, frozen=True)
class FileHistory:
    file: str
    commits: int
    additions: int
    deletions: int
    churn: int
    authors: int
    primary_author: str | None
    primary_share: float
    bus_factor: int
    structural_risk: float
    historical_risk: float
    risk_score: float


@dataclass(slots=True, frozen=True)
class Coupling:
    left: str
    right: str
    commits: int
    confidence: float


class GitHistoryAnalysis:
    """Derive churn, ownership, coupling and socio-technical risk from Git."""

    def __init__(
        self,
        root: str | Path,
        analysis: GraphAnalysis | None = None,
        *,
        since: str | None = "1 year ago",
        max_commits: int = 500,
    ) -> None:
        self.root = Path(root).resolve()
        self.analysis = analysis
        self.since = since
        self.max_commits = max(1, max_commits)
        self.commit_count = 0
        self.file_commits: Counter[str] = Counter()
        self.file_additions: Counter[str] = Counter()
        self.file_deletions: Counter[str] = Counter()
        self.file_authors: dict[str, Counter[str]] = defaultdict(Counter)
        self.coupling: Counter[tuple[str, str]] = Counter()
        self._read_history()

    def _git(self, *args: str) -> str:
        command = ["git", "-C", str(self.root), *args]
        try:
            completed = subprocess.run(
                command,
                check=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
        except FileNotFoundError as exc:
            raise GitHistoryError("git executable was not found") from exc
        except subprocess.CalledProcessError as exc:
            message = exc.stderr.strip() or "git history command failed"
            raise GitHistoryError(message) from exc
        return completed.stdout

    def _read_history(self) -> None:
        self._git("rev-parse", "--is-inside-work-tree")
        args = [
            "log",
            f"--max-count={self.max_commits}",
            "--no-merges",
            "--numstat",
            "--format=--CODEATLAS--%H%x09%aN%x09%aE",
        ]
        if self.since:
            args.append(f"--since={self.since}")
        output = self._git(*args)

        author = "Unknown"
        changed_files: set[str] = set()

        def finish_commit() -> None:
            if not changed_files:
                return
            self.commit_count += 1
            ordered = sorted(changed_files)
            for file in ordered:
                self.file_commits[file] += 1
                self.file_authors[file][author] += 1
            for left, right in combinations(ordered, 2):
                self.coupling[(left, right)] += 1
            changed_files.clear()

        for raw_line in output.splitlines():
            line = raw_line.rstrip("\n")
            if line.startswith("--CODEATLAS--"):
                finish_commit()
                parts = line.removeprefix("--CODEATLAS--").split("\t", 2)
                name = parts[1].strip() if len(parts) > 1 else "Unknown"
                email = parts[2].strip() if len(parts) > 2 else ""
                author = f"{name} <{email}>" if email else name
                continue
            fields = line.split("\t", 2)
            if len(fields) != 3:
                continue
            additions, deletions, file = fields
            if not file:
                continue
            changed_files.add(file)
            if additions.isdigit():
                self.file_additions[file] += int(additions)
            if deletions.isdigit():
                self.file_deletions[file] += int(deletions)
        finish_commit()

    def _structural_risk_by_file(self) -> dict[str, float]:
        if self.analysis is None:
            return {}
        grouped: dict[str, list[float]] = defaultdict(list)
        for hotspot in self.analysis.hotspots(limit=len(self.analysis.symbols)):
            grouped[hotspot.file].append(hotspot.risk_score)
        return {
            file: round(sum(scores) / len(scores), 2)
            for file, scores in grouped.items()
            if scores
        }

    @staticmethod
    def _bus_factor(authors: Counter[str]) -> int:
        total = sum(authors.values())
        if total <= 0:
            return 0
        covered = 0
        for position, touches in enumerate(sorted(authors.values(), reverse=True), start=1):
            covered += touches
            if covered / total >= 0.5:
                return position
        return len(authors)

    def files(self, *, limit: int | None = None) -> list[FileHistory]:
        structural = self._structural_risk_by_file()
        max_commits = max(self.file_commits.values(), default=1)
        max_churn = max(
            (self.file_additions[file] + self.file_deletions[file] for file in self.file_commits),
            default=1,
        )
        rows: list[FileHistory] = []
        for file, commits in self.file_commits.items():
            additions = self.file_additions[file]
            deletions = self.file_deletions[file]
            churn = additions + deletions
            authors = self.file_authors[file]
            primary_author, primary_touches = authors.most_common(1)[0] if authors else (None, 0)
            primary_share = round(primary_touches / commits, 3) if commits else 0.0
            history_risk = round(
                100
                * (
                    0.55 * math.log1p(commits) / math.log1p(max_commits)
                    + 0.45 * math.log1p(churn) / math.log1p(max_churn)
                ),
                2,
            )
            structural_risk = structural.get(file, 0.0)
            normalized_structural = min(100.0, structural_risk * 4.0)
            combined = round(0.58 * history_risk + 0.42 * normalized_structural, 2)
            rows.append(
                FileHistory(
                    file=file,
                    commits=commits,
                    additions=additions,
                    deletions=deletions,
                    churn=churn,
                    authors=len(authors),
                    primary_author=primary_author,
                    primary_share=primary_share,
                    bus_factor=self._bus_factor(authors),
                    structural_risk=structural_risk,
                    historical_risk=history_risk,
                    risk_score=combined,
                )
            )
        ranked = sorted(rows, key=lambda row: (-row.risk_score, -row.commits, row.file))
        return ranked if limit is None else ranked[: max(0, limit)]

    def couplings(self, *, limit: int = 30, minimum_commits: int = 2) -> list[Coupling]:
        rows: list[Coupling] = []
        for (left, right), commits in self.coupling.items():
            if commits < minimum_commits:
                continue
            denominator = min(self.file_commits[left], self.file_commits[right])
            confidence = round(commits / denominator, 3) if denominator else 0.0
            rows.append(Coupling(left, right, commits, confidence))
        return sorted(rows, key=lambda row: (-row.commits, -row.confidence, row.left, row.right))[:limit]

    def summary(self) -> dict[str, Any]:
        files = self.files()
        ownership_risks = [row for row in files if row.primary_share >= 0.8 and row.commits >= 3]
        return {
            "period": self.since,
            "commit_count": self.commit_count,
            "file_count": len(files),
            "author_count": len({author for authors in self.file_authors.values() for author in authors}),
            "single_owner_file_count": len(ownership_risks),
            "files": [asdict(row) for row in files],
            "couplings": [asdict(row) for row in self.couplings()],
        }
