# Software Requirements Specification
## PRD-to-Test-Case Generator (Multi-Agent, Local LLM)

Version 1.0 | Stack: Python, LangGraph, Ollama, LangChain/LlamaIndex, GitHub Actions

---

## 1. Problem Definition

### 1.1 Problem
Writing test cases from a Product Requirements Document (PRD) is slow, manual, and error-prone. Testers miss edge cases, negative paths, and non-functional requirements buried in long documents. Existing LLM tools hallucinate requirements, lose context on long documents, and give no measurable coverage signal.

### 1.2 Proposed Solution
A local, privacy-preserving multi-agent pipeline that:
1. Parses a PRD and splits it into chunks.
2. Extracts atomic, testable **requirement points** from each chunk.
3. Generates test cases per requirement point.
4. Has a **Critic agent** review quality and PRD coverage, and send feedback to the **Generator agent** for up to **5 refinement loops**.
5. Exports the final test suite plus a traceability (coverage) matrix.

All LLMs run locally via **Ollama**. Agents communicate through a shared **blackboard** implemented as LangGraph state.

### 1.3 Users and Experience Design
| User | Goal | Experience |
|---|---|---|
| QA engineer | Get a reviewed test suite from a PRD quickly | Upload PRD, run CLI/UI, download CSV/JSON/Markdown |
| Product manager | Check whether the PRD is testable | Read the coverage report and flagged ambiguities |
| Developer | Understand and extend the system | Ask the RAG bot questions about the codebase and docs |

Interaction surfaces:
- **CLI** (primary): `tcgen run --prd path/to/prd.pdf --out ./out`
- **Streamlit/Gradio UI** (optional): upload, live progress per loop, download results.
- **RAG Q&A bot**: chat over the project's code and docs (see 4.6).

Experience principles: visible progress (show loop number and critic score), explainable output (every test case links to a requirement point and a PRD chunk), and accessible output formats (see 6.3).

---

## 2. Scope

**In scope:** PRD ingestion (PDF, DOCX, MD, TXT), chunking, requirement extraction, test generation, critique loop, coverage report, export, RAG Q&A bot over the repository, CI/CD, automated test generation for the project's own code, documentation.

**Out of scope:** executing test cases, test automation script generation (future work), cloud-hosted LLMs.

---

## 3. System Architecture

### 3.1 Agents (LangGraph nodes)
| Node | Responsibility | Suggested Ollama model |
|---|---|---|
| `ingest` | Load and parse the document, preserve headings and sections | none (parser libraries) |
| `chunker` | Section-aware chunking with overlap, attach metadata (section path, page) | none (embedding-aided optional) |
| `extractor` | Convert each chunk into atomic requirement points (functional, non-functional, constraint, ambiguity) | `qwen2.5:7b-instruct` or `llama3.1:8b` |
| `generator` | Create test cases per requirement point; revise using critic feedback | `qwen2.5:14b-instruct` or `llama3.1:8b` |
| `critic` | Score quality and coverage, produce structured feedback | different family from generator, e.g. `deepseek-r1:8b` or `mistral:7b-instruct` |
| `coverage_checker` | Deterministic check: which requirement points have no test case | no LLM (set logic) |
| `exporter` | Write final CSV/JSON/MD and traceability matrix | none |
| Embeddings | RAG and semantic coverage matching | `nomic-embed-text` |

Using a different model family for the critic reduces self-agreement bias. Model names must live in config, never hard-coded.

### 3.2 Blackboard Design
The blackboard is the single shared LangGraph state (`TypedDict` or Pydantic model). Agents never call each other directly; they read from and write to named sections.

| Section | Written by | Read by | Content |
|---|---|---|---|
| `document` | ingest | chunker | raw text, structure |
| `chunks` | chunker | extractor | list of chunk objects with IDs and metadata |
| `requirement_points` | extractor | generator, critic, coverage_checker | `{id, text, type, priority, chunk_id}` |
| `test_cases` | generator | critic, exporter | `{id, req_ids, title, preconditions, steps, expected, type, priority}` |
| `critique` | critic | generator | `{score, coverage_score, issues[], missing_req_ids[], suggestions[]}` |
| `coverage` | coverage_checker | critic, exporter | covered/uncovered requirement IDs |
| `iteration` | graph | router | current loop count |
| `history` | all | exporter, UI | append-only log of versions and scores |
| `config` | CLI | all | models, thresholds, limits |

Rules: append-only history, schema-validated writes, every item carries a stable ID for traceability.

### 3.3 Graph Flow
```
ingest -> chunker -> extractor -> generator -> coverage_checker -> critic -> router
router: if (score >= threshold AND coverage >= target) OR iteration >= 5 -> exporter
        else -> generator (with critique on blackboard)
```
Stop conditions: quality score >= 8/10 and coverage >= 95%, or 5 loops reached, or no score improvement for 2 consecutive loops. The max loop count is configurable but capped at 5.

---

## 4. Functional Requirements

### 4.1 Document Ingestion and Chunking
- FR-1: Support PDF, DOCX, Markdown, and TXT.
- FR-2: Preserve heading hierarchy and tables.
- FR-3: Section-aware chunking (target 500-1000 tokens, 10-15% overlap), never splitting inside a table row or numbered list item where avoidable.
- FR-4: Each chunk has `chunk_id`, `section_path`, `page`.

### 4.2 Requirement Point Extraction
- FR-5: Output atomic, testable statements in structured JSON validated by Pydantic.
- FR-6: Classify as functional, non-functional, business rule, constraint, or ambiguity.
- FR-7: Flag vague statements ("fast", "user friendly") as ambiguities instead of inventing thresholds.
- FR-8: Deduplicate points across chunks.

### 4.3 Test Case Generation
- FR-9: Each test case includes ID, linked requirement IDs, title, preconditions, steps, test data, expected result, type (positive, negative, boundary, edge, security, performance), priority.
- FR-10: Every requirement point gets at least one positive and, where applicable, one negative or boundary case.
- FR-11: Generation is batched per requirement group to fit local model context limits.

### 4.4 Critic Agent
- FR-12: Score on a rubric: correctness vs PRD, clarity, atomicity, completeness of steps, traceability, diversity of test types. Return numeric scores and issues as structured JSON.
- FR-13: Receive deterministic coverage results and add semantic coverage judgement (are the right scenarios covered, not just referenced).
- FR-14: Report hallucination risk: test cases that assert behaviour not present in the PRD.
- FR-15: Feedback must be specific and actionable (reference test case IDs and missing requirement IDs).

### 4.5 Feedback Loop
- FR-16: Maximum 5 generator-critic iterations, enforced in the router, not by the LLM.
- FR-17: On revision, the generator changes only flagged test cases and adds missing ones, not regenerate everything.
- FR-18: Persist every iteration's output and critique for audit.
- FR-19: Handle malformed LLM output with retry (max 2) and JSON repair before failing the node.

### 4.6 RAG-Based Q&A Bot
- FR-20: A Q&A bot built with **LangChain or LlamaIndex** that answers questions about the project: code, README, this SRS, and optionally the processed PRD and generated tests.
- FR-21: Ingest repository files, chunk by language-aware splitters, embed with Ollama (`nomic-embed-text`), store in a local vector DB (Chroma or FAISS).
- FR-22: Answers cite source files and line ranges.
- FR-23: CLI command `tcgen ask "How does the router decide to stop?"` and a chat tab in the UI.
- FR-24: Include an evaluation set of at least 15 question/answer pairs and report retrieval hit rate.

### 4.7 Export
- FR-25: Export CSV, JSON, and Markdown.
- FR-26: Traceability matrix: requirement ID to test case IDs, with uncovered requirements listed.
- FR-27: Run report: models used, loops taken, final scores, token and time stats.

---

## 5. Developer Tooling and Automation Requirements (mapped to rubric)

### 5.1 Source Graph and Semantic Code Navigation
- Set up **Sourcegraph** (local Docker instance or Sourcegraph Cloud/Cody free tier) indexed against the repository.
- Document how to use code search, "find references", and "go to definition" on the repo, with screenshots in `docs/`.
- Provide at least 5 example navigation queries (for instance, find all writers to the `critique` blackboard key) in `docs/code-navigation.md`.

### 5.2 Tool Configuration and Code Exploration
- Provide config files for Cursor/Antigravity: `.cursor/rules` (or equivalent) describing architecture, coding standards, and blackboard conventions.
- `pyproject.toml` with ruff, mypy, pytest configured; `pre-commit` hooks.
- `docs/tooling.md` explaining how each tool was configured and used for exploration.

### 5.3 Prompt Engineering for Code Completion and Refactoring
- Maintain a `docs/prompts/` folder with the prompts used for code generation and refactoring, each recording: goal, prompt, result, and what was changed after review.
- Include at least 3 refactoring prompts with before/after diffs (for example, extracting a shared LLM client factory).
- Agent prompts used at runtime live in `src/tcgen/prompts/` as versioned template files, not inline strings.

### 5.4 CI/CD with GitHub Actions and Sweep.dev
- Workflow `ci.yml`: lint (ruff), type check (mypy), unit tests (pytest) with coverage on every push and PR. Ollama-dependent tests use a mocked LLM client so CI needs no GPU.
- Workflow `docs.yml` (optional): build and publish docs.
- **Sweep.dev**: configure `sweep.yaml` so GitHub issues labeled for Sweep produce automated PRs (for example, "add DOCX table parsing", "fix typo in docs"). Document at least 2 issues handled this way, with links.
- Note: verify the current availability and setup method of Sweep.dev before starting, as the product has changed over time. If the hosted GitHub bot is unavailable, use the closest supported alternative and document the deviation.

### 5.5 Test Generation with Codium AI/Codeium
- Use Codium AI (now branded Qodo) or Codeium to generate unit tests for at least 3 modules (chunker, router, JSON-repair utility).
- Keep generated tests in `tests/`, reviewed and edited by hand, with a note on what the tool got wrong or missed in `docs/test-generation.md`.
- Target at least 80% line coverage on non-LLM code.

### 5.6 Documentation and Accessibility of Implementation
- `README.md` with quickstart (under 10 minutes), architecture diagram, and model pull commands.
- `docs/architecture.md` (graph diagram in Mermaid, blackboard schema), `docs/user-guide.md`, `docs/developer-guide.md`.
- Docstrings on all public functions; type hints throughout.
- Accessibility: documentation uses semantic headings, alt text on images, no information conveyed by color alone; exported reports readable by screen readers (Markdown/CSV, plus accessible HTML option); UI (if built) supports keyboard navigation and sufficient contrast; CLI output usable without color via `--no-color`.

### 5.7 Integration Quality
- A single `make` or script entry point runs the whole flow end to end.
- An integration test runs the full graph on a small sample PRD using a stubbed LLM.
- Demonstrate that Sourcegraph, RAG bot, CI, Sweep, and test generation tools all work against the same repo, summarized in `docs/integration-report.md`.

---

## 6. Non-Functional Requirements

### 6.1 Performance
- A 20-page PRD processed end to end in under 30 minutes on a laptop with a 7-8B model (configurable).
- Models loaded sequentially to fit within local VRAM/RAM; model keep-alive configurable.

### 6.2 Reliability and Quality
- Structured output validation on every agent boundary.
- Deterministic router and coverage logic (no LLM decides loop termination).
- Seeded runs where Ollama supports it (`temperature` low for extractor/critic, moderate for generator).

### 6.3 Privacy and Portability
- No document content leaves the machine. No cloud LLM calls.
- Works on Windows, macOS, Linux. Configuration via `config.yaml` and environment variables.

### 6.4 Maintainability
- Modular layout, dependency injection for the LLM client, 80%+ coverage on non-LLM code.

---

## 7. Evaluation Plan

| Metric | Method | Target |
|---|---|---|
| Requirement coverage | covered points / total points | >= 95% |
| Test case quality | critic rubric average (0-10) | >= 8 |
| Hallucination rate | test cases referencing facts absent from PRD, found by manual sample of 30 | <= 5% |
| Loop benefit | score at loop 1 vs final | measurable improvement |
| Extraction recall | manual gold set of 2 PRDs | >= 85% |
| RAG quality | hit rate on 15-question eval set | >= 80% |

Include an ablation: single-pass generation vs critic-loop generation, reporting the difference.

---

## 8. Proposed Repository Layout
```
tcgen/
  src/tcgen/
    graph.py            # LangGraph assembly and router
    state.py            # Blackboard schema (Pydantic)
    config.py
    llm.py              # Ollama client factory
    nodes/              # ingest, chunker, extractor, generator, critic, coverage, exporter
    prompts/
    rag/                # indexer, retriever, qa chain
    cli.py
  tests/
  docs/
  .github/workflows/ci.yml
  sweep.yaml
  .cursor/rules/
  pyproject.toml  config.yaml  README.md  Makefile
```

---

## 9. Rubric Traceability

| Rubric item | Weight | Where addressed |
|---|---|---|
| Synopsis finalization / problem definition and experience design | 5% | Sections 1, 2 |
| Prompt engineering for code completion and refactoring | 5% | 5.3 |
| Source graph setup and semantic code navigation | 10% | 5.1 |
| Tool configuration and code exploration | 5% | 5.2 |
| Documentation and accessibility of implementation | 5% | 5.6 |
| RAG-based Q&A bot (LangChain or LlamaIndex) | 10% | 4.6 |
| GitHub Actions CI/CD with Sweep.dev | 10% | 5.4 |
| Test generation with Codium AI/Codeium | 5% | 5.5 |
| Integration quality and documentation | 5% | 5.7 |

---

## 10. Risks and Mitigations
| Risk | Mitigation |
|---|---|
| Small local models produce invalid JSON | Pydantic validation, retries, JSON repair, constrained output via Ollama `format` |
| Critic and generator agree too easily | Different model families, rubric with required evidence, deterministic coverage check |
| Context overflow on long PRDs | Chunking, per-group generation, summaries on the blackboard |
| Loops don't converge | Hard cap of 5, early stop on no improvement, keep best-scoring version |
| Sweep.dev or Codium availability/branding changes | Verify early, document alternatives |