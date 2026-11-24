"""LangGraph blackboard state shared by all pipeline nodes."""

from __future__ import annotations

from typing import Any, TypedDict

from tcgen.models import (
    Chunk,
    CoverageReport,
    Critique,
    Document,
    IterationRecord,
    RequirementPoint,
    TestCase,
)


class GraphState(TypedDict, total=False):
    """Named blackboard sections updated by LangGraph nodes."""

    prd_path: str
    out_dir: str
    document: Document
    chunks: list[Chunk]
    requirement_points: list[RequirementPoint]
    test_cases: list[TestCase]
    critique: Critique
    coverage: CoverageReport
    iteration: int
    history: list[IterationRecord]
    stale_iterations: int
    config: dict[str, Any]
    started_at: float
    elapsed_seconds: float
    token_stats: dict[str, int]
    run_report: dict[str, Any]
