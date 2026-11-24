"""Deterministic requirement coverage calculations."""

from __future__ import annotations

from tcgen.models import CoverageReport, RequirementPoint, TestCase, TestType


def check_coverage(
    requirements: list[RequirementPoint], test_cases: list[TestCase]
) -> CoverageReport:
    """Map every known requirement to linked cases without an LLM judgement."""
    requirement_ids = {point.id for point in requirements}
    mapping: dict[str, list[str]] = {point.id: [] for point in requirements}
    for case in test_cases:
        for requirement_id in case.req_ids:
            if requirement_id in requirement_ids:
                mapping[requirement_id].append(case.id)
    covered = [requirement_id for requirement_id, cases in mapping.items() if cases]
    uncovered = [requirement_id for requirement_id, cases in mapping.items() if not cases]
    missing_positive = [
        point.id
        for point in requirements
        if not any(
            point.id in case.req_ids and case.type == TestType.POSITIVE for case in test_cases
        )
    ]
    return CoverageReport(
        covered_requirement_ids=covered,
        uncovered_requirement_ids=uncovered,
        missing_positive_requirement_ids=missing_positive,
        test_cases_by_requirement=mapping,
    )
