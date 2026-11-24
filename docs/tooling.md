# Tooling and code exploration

## Configured local tools

- **Ruff**: lint and format via `pyproject.toml`; run `ruff check .` and
  `ruff format --check .`.
- **mypy**: strict project type-check with `src` as the import root.
- **pytest/coverage**: tests use injected stub model clients so CI is offline with
  respect to LLMs. Coverage threshold is configured in `pyproject.toml`.
- **pre-commit**: `.pre-commit-config.yaml` runs Ruff, formatting, and mypy.
- **Cursor**: `.cursor/rules/tcgen.mdc` records graph, privacy, prompt, and test rules.
- **GitHub Actions**: `.github/workflows/ci.yml` runs install, lint, type-check and
  tests for pushes and pull requests.
- **Ollama**: `config.yaml` configures extractor/generator/critic/embedding models;
  `TCGEN_OLLAMA_BASE_URL` and role-specific model environment variables may override
  local values.

## Exploration workflow used

1. Read the requirements and `Agents.md` before changing files.
2. Inspect the current source tree and working tree.
3. Trace each requirement through the graph nodes and blackboard schema.
4. Search for callers before changing a shared boundary.
5. Use injectable models to test graph behavior independently of Ollama.

No claims are made that a hosted Sourcegraph instance, Sweep bot, or Qodo service was
authenticated or exercised in this environment.
