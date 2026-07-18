"""Command-line interface for CodeAtlas."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .analysis import GraphAnalysis
from .indexer import PythonIndexer
from .web import build_payload, render_html, serve


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
    parser.add_argument("--html", type=Path, help="Write a self-contained interactive HTML explorer")
    parser.add_argument("--serve", action="store_true", help="Launch the local interactive graph explorer")
    parser.add_argument("--host", default="127.0.0.1", help="Explorer bind address (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8765, help="Explorer port (default: 8765; use 0 for any free port)")
    parser.add_argument("--no-browser", action="store_true", help="Do not open a browser with --serve")
    parser.add_argument("--impact", metavar="SYMBOL", help="List transitive callers affected by a symbol change")
    parser.add_argument("--impact-depth", type=int, help="Maximum caller depth used with --impact")
    parser.add_argument("--fail-on-errors", action="store_true", help="Exit non-zero when files could not be parsed")
    parser.add_argument("--fail-on-cycles", action="store_true", help="Exit non-zero when resolved dependency cycles exist")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not 0 <= args.port <= 65535:
        print("codeatlas: --port must be between 0 and 65535", file=sys.stderr)
        return 2

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

    if args.html:
        args.html.parent.mkdir(parents=True, exist_ok=True)
        args.html.write_text(render_html(build_payload(index, analysis)), encoding="utf-8")
        print(f"Interactive explorer -> {args.html}")

    serialized = json.dumps(payload, indent=None if args.compact else 2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized + "\n", encoding="utf-8")
        summary = payload["summary"]
        print(
            f"Indexed {summary['file_count']} files, {summary['symbol_count']} symbols, "
            f"{summary['dependency_count']} dependencies -> {args.output}"
        )
    elif not args.serve and not args.html:
        print(serialized)

    if args.fail_on_errors and index.errors:
        return 1
    if args.fail_on_cycles and analysis.cycles():
        return 1
    if args.serve:
        try:
            serve(index, analysis, host=args.host, port=args.port, open_browser=not args.no_browser)
        except OSError as exc:
            print(f"codeatlas: could not start explorer: {exc}", file=sys.stderr)
            return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
