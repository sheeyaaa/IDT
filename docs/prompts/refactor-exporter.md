# Refactoring prompt: shared report export

Status: illustrative prompt record; no external code-generation service was invoked.

## Goal

Export a consistent test-suite representation in accessible and machine-readable formats.

## Prompt

> Inspect the test-case and coverage models. Write a single exporter that preserves
> traceability across JSON, CSV, Markdown, and semantic HTML; escape untrusted text and
> do not omit uncovered requirement IDs.

## Result

Added `export_suite` with shared typed inputs and JSON/CSV/Markdown/HTML output.

## Review change

HTML content is escaped and tabular headers/caption are semantic. CSV uses UTF-8 with
BOM for spreadsheet compatibility; Markdown remains the primary accessible narrative.

## Before / after

```diff
- write cases directly from separate CLI branches
+ export_suite(out_dir, requirements, cases, coverage, critique, report)
```
