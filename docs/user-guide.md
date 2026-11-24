# User guide

## Generate a suite

Run `tcgen run --prd PATH --out DIRECTORY`. Supported PRD extensions are PDF, DOCX,
Markdown, and TXT. PDF page text is kept page-by-page; DOCX paragraph and table order
is retained; Markdown headings and tables are retained as text. Unsupported extensions
and documents with no extractable text produce explicit errors.

The CLI prints a plain-text score and coverage line per critic loop. Use `--no-color`
for log capture and assistive technology workflows (output is plain by default).

## Configure local models

The checked-in `config.yaml` defines the local Ollama endpoint, per-role model names,
temperatures, thresholds, chunk/batch sizes, retry limit, keep-alive seconds, and
Chroma directory. Do not point the endpoint at a hosted model service. Supported
environment overrides are documented in the README. `max_iterations` is validated
between one and five. The graph unloads a role model before switching roles; setting
keep-alive to `0` unloads after each request for the lowest memory use, at the cost of
reloading for every chunk/request.

## Read exports

- `test-suite.json`: complete typed data, history and report fields.
- `test-cases.csv`: one case per row; list fields are newline-separated.
- `test-suite.md`: headings, traceability, uncovered requirements, and run report.
- `test-suite.html`: semantic table headers and caption for screen readers.

The critic's quality/coverage score and deterministic ID-link coverage are both
reported; neither score should replace human review, especially for ambiguity points
and hallucination risks.

## Ask questions about this repository

Run `tcgen index .` once to create/update the local Chroma index. Then use
`tcgen ask "question"` for cited answers or `tcgen eval-rag` for expected-source hit
rate. Re-run index after code or documentation changes. Indexing skips virtual
environments, build output, hidden VCS internals, and files larger than 1 MB.
