# Test generation tool record

## Modules and review notes

The focused suite in `tests/` covers the chunker, deterministic coverage, bounded
JSON repair, and an end-to-end stubbed graph. Tests were authored and reviewed against
the requirements in this workspace. Qodo (formerly Codium AI) / Codeium was not
available or authenticated in this environment, so these tests are not represented as
tool-generated; using either product and documenting its generated output remains an
external follow-up.

Review focus: verify that headings/tables remain attached to chunk metadata, the router
cannot exceed five generator/critic cycles, invalid model output raises rather than
returning a plausible fallback, and graph tests require neither Ollama nor network
access.
