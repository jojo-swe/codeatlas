"""Command-line interface for CodeAtlas."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .indexer import PythonIndexer


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="codeatlas",
        description="Index a Python repository and export its symbol/dependency graph.",
    )
    parser.add_argument("path", nargs="?", default=".", help="Repository path (default: current directory)")
    parser.add_argument("--output", "-o", type=Path, help="Write JSON result to this file")
    parser.add_argument("--compact", action="store_true", help="Emit compact JSON")
    parser.add_argument("--fail-on-errors", action="store_true", help="Exit non-zero when files could not be parsed")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        index = PythonIndexer(args.path).index()
    except (FileNotFoundError, NotADirectoryError) as exc:
        print(f"codeatlas: {exc}", file=sys.stderr)
        return 2

    payload = index.to_json(indent=None if args.compact else 2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload + "\n", encoding="utf-8")
        summary = index.to_dict()["summary"]
        print(
            f"Indexed {summary['file_count']} files, {summary['symbol_count']} symbols, "
            f"{summary['dependency_count']} dependencies -> {args.output}"
        )
    else:
        print(payload)

    return 1 if args.fail_on_errors and index.errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
