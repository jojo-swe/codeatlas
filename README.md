# CodeAtlas

CodeAtlas turns a Python repository into a navigable symbol and dependency graph without executing the target code.

The current alpha indexes:

- Python modules and files
- Classes, functions, methods, and async functions
- Imports
- Inheritance relationships
- Function and method calls
- Parse errors without aborting the full scan

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
    "symbol_count": 31
  }
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
Serializable CodeIndex
   |
   +--> JSON
   +--> Future web visualizer
```

## Development

```bash
pip install -e ".[dev]"
ruff check .
pytest
```

## Near-term roadmap

- Resolve call targets to known symbols
- Add graph filtering and search
- Export Graphviz and Mermaid
- Add repository statistics and hotspots
- Add a local interactive web UI
- Support JavaScript and TypeScript through pluggable language adapters

## Status

`0.1.0-alpha` is a working vertical slice, not a finished code-intelligence platform. The core file discovery, AST analysis, relationship extraction, JSON serialization, tests, and CI are implemented.

## License

Apache License 2.0.
