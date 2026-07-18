# CodeAtlas

CodeAtlas turns a Python repository into an interactive symbol, dependency, change-impact and engineering-risk map without executing the target code.

The current alpha provides:

- Python module, class, function, method and async-function indexing
- Import, inheritance and call relationships
- Dependency-cycle detection
- Structural hotspot and risk ranking
- Transitive change-impact analysis
- Local Git churn, ownership, bus-factor and temporal-coupling analysis
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

## Git intelligence

Combine the static graph with local repository history:

```bash
codeatlas . --analysis --git --output atlas.json
```

The Git layer reports:

- commits and line churn per file
- primary ownership and ownership concentration
- file-level bus factor
- files that repeatedly change together
- temporal-coupling confidence
- combined structural and historical risk

The default history window is one year and at most 500 commits. Both are configurable:

```bash
codeatlas . --git --git-since "2 years ago" --git-max-commits 2000
codeatlas . --git --git-since all
```

Use ownership concentration as a CI guardrail:

```bash
codeatlas . --git --fail-on-single-owner --output atlas.json
```

This fails when a file has at least three inspected commits and one author owns at least 80 percent of them. Git inspection is local and read-only; CodeAtlas never fetches from a remote.

## Portable interactive report

Export the complete explorer as one self-contained HTML file:

```bash
codeatlas . --html codeatlas-report.html
```

Include Git data in the embedded report payload:

```bash
codeatlas . --git --html codeatlas-report.html
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
- `1`: an enabled parse, cycle or ownership guardrail failed
- `2`: invalid input, unavailable Git history, unknown symbol or explorer startup failure

## Architecture

```text
Repository
   |
   +--> Python discovery + AST parser (no code execution)
   |       +--> Symbol index
   |       +--> Import / inheritance / call graph
   |
   +--> Local Git log (read-only)
           +--> Churn and ownership
           +--> Bus factor
           +--> Temporal coupling
   |
   v
Graph intelligence
   +--> Tarjan cycle detection
   +--> Structural hotspot ranking
   +--> Historical and combined risk
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

- Surface Git risk and coupling as first-class interactive UI panels
- Resolve aliased and relative imports more deeply
- Add module- and package-level aggregation
- Add architecture-policy files and forbidden-edge checks
- Support JavaScript and TypeScript through language adapters

## Status

CodeAtlas is an active alpha. It already provides a complete local path from repository discovery and history inspection to actionable graph and socio-technical risk analysis. Language resolution remains intentionally conservative and unresolved external relationships remain visible in the analysis summary.

## License

Apache License 2.0.
