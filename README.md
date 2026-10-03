# CodeAtlas

CodeAtlas turns a Python repository into an interactive symbol, dependency, change-impact and engineering-risk map without executing the target code.

The current alpha provides:

- Python module, class, function, method and async-function indexing
- Import, inheritance and call relationships
- Confidence-aware resolution of calls and inheritance targets
- Dependency-cycle detection
- Structural hotspot and risk ranking
- Transitive change-impact analysis
- Local Git churn, ownership, bus-factor and temporal-coupling analysis
- Declarative architecture layers and forbidden-dependency policies
- JSON export, including resolution confidence
- Deterministic Mermaid export of the full graph
- Mermaid export of the resolved symbol graph
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

Index the repository as JSON:

```bash
codeatlas . --output codeatlas.json
```

Print compact JSON to stdout:

```bash
codeatlas . --compact
```

## Symbol resolution

Each dependency keeps its original target. Resolvable calls and inheritance relationships also record where that target landed and how confident the match is:

```json
{
  "source": "app.main",
  "target": "Worker.run",
  "kind": "calls",
  "resolved_target": "app.Worker.run",
  "confidence": 0.95,
  "resolution": "same-module"
}
```

The index summary includes `resolved_dependency_count` beside the raw dependency and symbol counts. Resolution is conservative: CodeAtlas records the raw target even when it cannot establish a unique destination, rather than inventing a relationship.

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

Export the deterministic full graph, including unresolved endpoints and confidence-aware targets, as Mermaid:

```bash
codeatlas . --format mermaid --output codeatlas.mmd
```

That Mermaid output is stable for the same index, which makes it suitable for generated documentation and reviewable CI artifacts.

Export only the resolved symbol-to-symbol graph:

```bash
codeatlas . --mermaid architecture.mmd
```

Graph analysis, cycles, change impact, architecture policies and this resolved diagram prefer an indexer `resolved_target` when it names a known symbol. Edges the indexer leaves unresolved still fall back to structural name matching.

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
   v
Confidence-aware symbol resolver
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
   +--> Confidence-aware targets when they name an indexed symbol
   +--> Tarjan cycle detection
   +--> Structural hotspot ranking
   +--> Historical and combined risk
   +--> Reverse-graph change impact
   |
   +--> JSON
   +--> Deterministic Mermaid (--format mermaid)
   +--> Resolved-symbol Mermaid (--mermaid)
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

- Expand target resolution across relative imports and package layouts
- Surface Git and policy risk as first-class interactive UI panels
- Add graph filtering and search beyond the explorer
- Export Graphviz
- Add module- and package-level aggregation
- Support JavaScript and TypeScript through pluggable language adapters

## Status

`0.2.0-alpha` is an active local code-intelligence slice. It already indexes a repository, resolves call and inheritance targets with confidence, and turns that graph into JSON, deterministic Mermaid, cycle and hotspot analysis, change impact, Git risk, architecture-policy checks, and a local explorer. Unresolved external relationships stay visible instead of being invented.

## License

Apache License 2.0.
