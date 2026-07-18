# CodeAtlas

CodeAtlas turns a Python repository into an interactive symbol, dependency, change-impact and engineering-risk map without executing the target code.

The current alpha provides:

- Python module, class, function, method and async-function indexing
- Import, inheritance and call relationships
- Dependency-cycle detection
- Structural hotspot and risk ranking
- Transitive change-impact analysis
- Local Git churn, ownership, bus-factor and temporal-coupling analysis
- Declarative architecture layers and forbidden-dependency policies
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

The browser opens at `http://127.0.0.1:8765` and provides a navigable dependency graph, symbol and file search, relationship filters, hotspots, dependency-cycle isolation and transitive change-impact exploration.

Nothing is uploaded and the analyzed repository is never executed.

## Architecture policies

CodeAtlas can enforce team-specific dependency boundaries from a version-controlled JSON file. Start with `codeatlas.policy.example.json`:

```json
{
  "layers": {
    "presentation": ["app.ui.*", "app/api/**"],
    "application": ["app.services.*", "app/use_cases/**"],
    "domain": ["app.domain.*", "app/domain/**"],
    "infrastructure": ["app.db.*", "app/infrastructure/**"]
  },
  "rules": [
    {
      "from": "presentation",
      "deny": ["infrastructure"],
      "message": "Presentation code must use the application layer"
    },
    {
      "from": "domain",
      "deny": ["presentation", "infrastructure"]
    }
  ]
}
```

Patterns are matched against both fully qualified symbol names and normalized repository-relative file paths. Rules may optionally apply only to selected relationship kinds:

```json
{
  "from": "presentation",
  "deny": ["infrastructure"],
  "kinds": ["calls", "imports"]
}
```

Evaluate the policy and include assignments and violations in JSON output:

```bash
codeatlas . --policy codeatlas.policy.json --output atlas.json
```

Turn it into a CI architecture gate:

```bash
codeatlas . \
  --policy codeatlas.policy.json \
  --fail-on-policy \
  --output atlas.json
```

Policy violations report the source and target symbols, relationship kind, assigned layers and the rule message. Invalid policies exit with code `2`; valid policies containing violations exit with code `1` when `--fail-on-policy` is enabled.

## Git intelligence

Combine the static graph with local repository history:

```bash
codeatlas . --analysis --git --output atlas.json
```

The Git layer reports commits and line churn per file, primary ownership, ownership concentration, file-level bus factor, temporal coupling and combined structural/historical risk.

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

Embed Git and architecture-policy data in the report payload:

```bash
codeatlas . --git --policy codeatlas.policy.json --html codeatlas-report.html
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

Combine guardrails in CI:

```bash
codeatlas . \
  --policy codeatlas.policy.json \
  --fail-on-errors \
  --fail-on-cycles \
  --fail-on-policy \
  --output atlas.json
```

Exit codes:

- `0`: scan completed and configured guardrails passed
- `1`: an enabled parse, cycle, ownership or architecture-policy guardrail failed
- `2`: invalid input, unavailable Git history, invalid policy, unknown symbol or explorer startup failure

## Architecture

```text
Repository
   |
   +--> Python discovery + AST parser (no code execution)
   |       +--> Symbol index
   |       +--> Import / inheritance / call graph
   |
   +--> Local Git log (read-only)
   |       +--> Churn and ownership
   |       +--> Bus factor
   |       +--> Temporal coupling
   |
   +--> Architecture policy
           +--> Layer assignment
           +--> Forbidden-edge checks
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

- Surface Git and policy risk as first-class interactive UI panels
- Resolve aliased and relative imports more deeply
- Add module- and package-level aggregation
- Support JavaScript and TypeScript through language adapters

## Status

CodeAtlas is an active alpha. It already provides a complete local path from repository discovery and history inspection to actionable graph, socio-technical risk and architecture-policy analysis. Language resolution remains intentionally conservative and unresolved external relationships remain visible in the analysis summary.

## License

Apache License 2.0.
