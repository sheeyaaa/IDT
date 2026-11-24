# Developer guide

## Setup and checks

Use Python 3.11+, then install `python -m pip install -e ".[dev]"`. Run
`ruff check .`, `ruff format --check .`, `mypy src`, and `pytest`. `make check` groups
the same commands where Make is available.

## Extend the graph

1. Add a Pydantic schema in `src/tcgen/models.py` for any new agent boundary.
2. Add a pure/injectable node under `src/tcgen/nodes/`.
3. Add the node and deterministic edges in `src/tcgen/graph.py`.
4. Place every new runtime prompt in `src/tcgen/prompts/`.
5. Cover new behavior with a fake `Invokable`; tests must not need a running Ollama
   server or download models.

Never add cloud model clients or inline runtime prompt text. Keep blackboard keys
explicit and source links stable. The graph's conditional route, rather than any model
response, is authoritative for the five-iteration cap. Production Ollama calls receive
Pydantic schemas through `with_structured_output`; do not paste JSON Schema into agent
prompts.

## Add an ingestion format

Extend `parse_document` with a format-specific parser, preserving source page/section
metadata as far as the format permits. Add an ingestion test with a small fixture;
keep table rows intact where possible.
