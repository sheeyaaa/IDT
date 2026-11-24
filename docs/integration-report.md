# Integration report

## Verified in this repository

- The LangGraph path is exercised end-to-end against injected JSON stub models by
  `tests/test_graph.py`.
- The configured GitHub Actions CI workflow includes Ruff, mypy, and pytest with a
  mocked LLM path, so no GPU is required.
- The local RAG implementation, Chroma persistence wiring, Ollama embeddings, source
  line metadata, CLI, and 15-query retrieval dataset are present. Live indexing and
  retrieval require the configured Ollama embedding model and have not been run here.
- Sweep configuration is present in `sweep.yaml`, but hosted bot availability could
  not be confirmed (the service hostname did not resolve in this environment); do
  not enable it until its current service and schema are independently confirmed.
  No issue-to-PR replacement was enabled without verified availability; manual GitHub
  issue handling plus the checked-in CI workflow is the safe fallback in this workspace.
- Sourcegraph setup and six example queries are documented in
  `docs/code-navigation.md`; no authenticated indexed instance or screenshots were
  available to verify.
- Qodo/Codeium test-generation use was not available/authenticated; tests were
  hand-authored and the deviation is recorded in `docs/test-generation.md`.

## Not verified

No live Ollama model, Chroma embedding call, hosted Sourcegraph indexing, Sweep issue
automation, Qodo/Codeium generation, or external issue-to-PR workflow was performed.
The evaluation dataset is a reproducible test input, not a measured hit-rate result.
