# CodeAtlas

CodeAtlas turns a Python repository into an interactive symbol, dependency and change-impact map without executing the target code.

The current alpha provides:

- Python module, class, function, method and async-function indexing
- Import, inheritance and call relationships
- Dependency-cycle detection
- Structural hotspot and risk ranking
- Transitive change-impact analysis
- JSON and Mermaid export
- A zero-dependency local web explorer
- Parse-error reporting without aborting the full scan

## Quick start

```bash
git clone https://github.com/jojo-swe/codeatlas.git
cd codeatlas
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

Launch the interactive explorer for any Python repository:

```bash
codeatlas /path/to/repository --serve
```

The browser opens at `http://127.0.0.1:8765` and provides:

- a navigable dependency graph
- symbol and file search
- filters for symbol and relationship kinds
- risk-ranked hotspots
- dependency-cycle isolation
- incoming and outgoing relationship inspection
- transitive change-impact exploration

Nothing is uploaded and the analyzed repository is never executed.

## Portable interactive report

Export the complete explorer as one self-contained HTML file:

```bash
codeatlas . --html codeatlas-report.html
```

The report has no CDN, Node.js or runtime-server dependency and can be opened directly in a browser.

## Analysis and automation

Generate enriched JSON:

```bash
codeatlas . --analysis --output atlas.json
```

Inspect callers that may be affected by changing a symbol:

```bash
codeatlas . --impact codeatlas.indexer.PythonIndexer.index
```

Export the resolved graph as Mermaid:

```bash
codeatlas . --mermaid architecture.mmd
```

Use CodeAtlas as a CI architecture guardrail:

```bash
codeatlas . --fail-on-errors --fail-on-cycles --output atlas.json
```

Exit codes:

- `0`: scan completed and configured guardrails passed
- `1`: parse errors or dependency cycles reached an enabled failure condition
- `2`: invalid input, unknown symbol or explorer startup failure

## Architecture

```text
Repository
   |
   v
Python discovery + AST parser (no code execution)
   |
   +--> Symbol index
   +--> Import / inheritance / call graph
   |
   v
Graph intelligence
   +--> Tarjan cycle detection
   +--> Hotspot and risk ranking
   +--> Reverse-graph change impact
   |
   +--> JSON
   +--> Mermaid
   +--> Self-contained HTML explorer
   +--> Local threaded web server
```

## Development

```bash
pip install -e ".[dev]"
ruff check .
pytest
```

## Near-term roadmap

- Resolve aliased and relative imports more deeply
- Add module- and package-level aggregation
- Add architecture-policy files and forbidden-edge checks
- Support JavaScript and TypeScript through language adapters
- Add Git-history-aware change risk and ownership metrics

## Status

CodeAtlas is an active alpha. It already provides a complete static-analysis path from repository discovery to actionable graph exploration, but its language resolution is intentionally conservative and unresolved external relationships remain visible in the analysis summary.

## License

Apache License 2.0.
