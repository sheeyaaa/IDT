"""Accessible test suite and traceability report exporters."""

from __future__ import annotations

import csv
import html
import json
from pathlib import Path
from typing import Any

from tcgen.models import (
    CoverageReport,
    Critique,
    IterationRecord,
    RequirementPoint,
    TestCase,
)


def export_suite(
    out_dir: Path,
    requirements: list[RequirementPoint],
    cases: list[TestCase],
    coverage: CoverageReport,
    critique: Critique | None,
    run_report: dict[str, Any],
    history: list[IterationRecord],
) -> None:
    """Write machine-readable and screen-reader-friendly reports."""
    out_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "requirements": [item.model_dump(mode="json") for item in requirements],
        "test_cases": [item.model_dump(mode="json") for item in cases],
        "coverage": coverage.model_dump(mode="json"),
        "critique": critique.model_dump(mode="json") if critique else None,
        "history": [record.model_dump(mode="json") for record in history],
        "run_report": run_report,
    }
    (out_dir / "test-suite.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    with (out_dir / "test-cases.csv").open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=[
                "id",
                "req_ids",
                "title",
                "preconditions",
                "steps",
                "test_data",
                "expected",
                "type",
                "priority",
            ],
        )
        writer.writeheader()
        for case in cases:
            row = case.model_dump(mode="json")
            for key in ("req_ids", "preconditions", "steps", "test_data"):
                row[key] = "\n".join(row[key])
            writer.writerow(row)

    matrix = []
    for point in requirements:
        requirement_text = point.text.replace("|", "\\|")
        case_ids = ", ".join(coverage.test_cases_by_requirement.get(point.id, [])) or "Uncovered"
        matrix.append(f"| {point.id} | {requirement_text} | {point.chunk_id} | {case_ids} |")
    markdown = [
        "# Generated test suite",
        "",
        f"Quality score: {critique.score:.1f}/10" if critique else "Quality score: unavailable",
        f"Requirement coverage: {critique.coverage_score:.1f}%"
        if critique
        else "Requirement coverage: unavailable",
        "",
        "## Test cases",
        "",
    ]
    for case in cases:
        markdown.extend(
            [
                f"### {case.id}: {case.title}",
                "",
                f"- Requirements: {', '.join(case.req_ids)}",
                f"- Type: {case.type.value}; priority: {case.priority}",
                f"- Preconditions: {'; '.join(case.preconditions) or 'None'}",
                "- Steps:",
                *[f"  {index}. {step}" for index, step in enumerate(case.steps, start=1)],
                f"- Test data: {'; '.join(case.test_data) or 'None'}",
                f"- Expected result: {case.expected}",
                "",
            ]
        )
    uncovered_items = [f"- {item}" for item in coverage.uncovered_requirement_ids]
    if not uncovered_items:
        uncovered_items = ["- None"]
    missing_positive_items = [f"- {item}" for item in coverage.missing_positive_requirement_ids]
    if not missing_positive_items:
        missing_positive_items = ["- None"]
    critic_gap_items = [f"- {item}" for item in (critique.missing_req_ids if critique else [])]
    if not critic_gap_items:
        critic_gap_items = ["- None"]
    markdown.extend(
        [
            "## Traceability matrix",
            "",
            "| Requirement ID | Requirement | Chunk ID | Test case IDs |",
            "|---|---|---|---|",
            *matrix,
            "",
            "## Uncovered requirements",
            "",
            *uncovered_items,
            "",
            "## Requirements without positive coverage",
            "",
            *missing_positive_items,
            "",
            "## Critic-reported remaining gaps",
            "",
            *critic_gap_items,
            "",
            "## Run report",
            "",
            "```json",
            json.dumps(run_report, indent=2),
            "```",
            "",
        ]
    )
    md_content = "\n".join(markdown)
    (out_dir / "test-suite.md").write_text(md_content, encoding="utf-8")
    rows = "".join(
        "<tr><td>"
        + html.escape(case.id)
        + "</td><td>"
        + html.escape(case.title)
        + "</td><td>"
        + html.escape(", ".join(case.req_ids))
        + "</td><td>"
        + html.escape("; ".join(case.steps))
        + "</td><td>"
        + html.escape(case.expected)
        + "</td></tr>"
        for case in cases
    )
    (out_dir / "test-suite.html").write_text(
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        "<title>Generated test suite</title></head><body><main><h1>Generated test suite</h1>"
        "<table><caption>Test cases and linked requirements</caption><thead><tr>"
        '<th scope="col">ID</th><th scope="col">Title</th><th scope="col">Requirements</th>'
        '<th scope="col">Steps</th><th scope="col">Expected result</th>'
        f"</tr></thead><tbody>{rows}</tbody></table></main></body></html>",
        encoding="utf-8",
    )
