"""Command-line interface for CodeAtlas."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .analysis import GraphAnalysis
from .indexer import PythonIndexer


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="codeatlas",
        description="Index a Python repository and analyze its symbol/dependency graph.",
    )
    parser.add_argument("path", nargs="?", default=".", help="Repository path (default: current directory)")
    parser.add_argument("--output", "-o", type=Path, help="Write JSON result to this file")
    parser.add_argument("--compact", action="store_true", help="Emit compact JSON")
    parser.add_argument("--analysis", action="store_true", help="Include hotspots, cycles and graph metrics")
    parser.add_argument("--mermaid", type=Path, help="Write the resolved graph as Mermaid flowchart syntax")
    parser.add_argument("--impact", metavar="SYMBOL", help="List transitive callers affected by a symbol change")
    parser.add_argument("--impact-depth", type=int, help="Maximum caller depth used with --impact")
    parser.add_argument("--fail-on-errors", action="store_true", help="Exit non-zero when files could not be parsed")
    parser.add_argument("--fail-on-cycles", action="store_true", help="Exit non-zero when resolved dependency cycles exist")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        index = PythonIndexer(args.path).index()
    except (FileNotFoundError, NotADirectoryError) as exc:
        print(f"codeatlas: {exc}", file=sys.stderr)
        return 2

    analysis = GraphAnalysis(index)
    payload = index.to_dict()
    if args.analysis:
        payload["analysis"] = analysis.summary()

    if args.impact:
        try:
            impacted = analysis.impact(args.impact, depth=args.impact_depth)
        except KeyError:
            print(f"codeatlas: unknown indexed symbol: {args.impact}", file=sys.stderr)
            return 2
        payload["impact"] = {"symbol": args.impact, "callers": impacted}

    if args.mermaid:
        args.mermaid.parent.mkdir(parents=True, exist_ok=True)
        args.mermaid.write_text(analysis.to_mermaid(), encoding="utf-8")

    serialized = json.dumps(payload, indent=None if args.compact else 2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized + "\n", encoding="utf-8")
        summary = payload["summary"]
        print(
            f"Indexed {summary['file_count']} files, {summary['symbol_count']} symbols, "
            f"{summary['dependency_count']} dependencies -> {args.output}"
        )
    else:
        print(serialized)

    if args.fail_on_errors and index.errors:
        return 1
    if args.fail_on_cycles and analysis.cycles():
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
