# CodeAtlas

CodeAtlas turns a Python repository into a navigable symbol and dependency graph without executing the target code.

The current alpha indexes:

- Python modules and files
- Classes, functions, methods, and async functions
- Imports
- Inheritance relationships
- Function and method calls
- Parse errors without aborting the full scan
- Confidence-aware resolution of calls and inheritance targets
- Deterministic Mermaid graph export

## Quick start

```bash
git clone https://github.com/jojo-swe/codeatlas.git
cd codeatlas
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
codeatlas /path/to/repository --output atlas.json
```

Example output:

```json
{
  "summary": {
    "dependency_count": 42,
    "error_count": 0,
    "file_count": 8,
    "resolved_dependency_count": 27,
    "symbol_count": 31
  }
}
```

Each resolvable call or inheritance relationship includes the original target plus:

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

Run against CodeAtlas itself:

```bash
codeatlas . --output codeatlas.json
```

Print compact JSON to stdout:

```bash
codeatlas . --compact
```

Export a Mermaid graph:

```bash
codeatlas . --format mermaid --output codeatlas.mmd
```

The Mermaid output is deterministic, making it suitable for generated documentation and reviewable CI artifacts.

Fail CI when source files cannot be parsed:

```bash
codeatlas . --fail-on-errors --output codeatlas.json
```

## Architecture

```text
Repository
   |
   v
Python file discovery
   |
   v
AST parser (no code execution)
   |
   +--> Symbol index
   +--> Import graph
   +--> Inheritance graph
   +--> Call graph
   |
   v
Confidence-aware symbol resolver
   |
   v
Serializable CodeIndex
   |
   +--> JSON
   +--> Mermaid
   +--> Future web visualizer
```

Resolution is conservative. CodeAtlas records the raw target even when it cannot establish a unique destination, rather than inventing a relationship.

## Development

```bash
pip install -e ".[dev]"
ruff check .
pytest
```

## Near-term roadmap

- Expand target resolution across relative imports and package layouts
- Add graph filtering and search
- Export Graphviz
- Add repository statistics and hotspots
- Add a local interactive web UI
- Support JavaScript and TypeScript through pluggable language adapters

## Status

`0.2.0-alpha` is a working code-intelligence vertical slice. The core file discovery, AST analysis, relationship extraction, confidence-aware target resolution, JSON and Mermaid serialization, tests, and CI are implemented.

## License

Apache License 2.0.
