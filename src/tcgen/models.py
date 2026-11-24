"""Validated data exchanged by the PRD processing agents."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    """Base model that rejects unrecognized model-generated fields."""

    model_config = ConfigDict(extra="forbid")


class RequirementType(StrEnum):
    """Kinds of atomic requirement points."""

    FUNCTIONAL = "functional"
    NON_FUNCTIONAL = "non-functional"
    BUSINESS_RULE = "business_rule"
    CONSTRAINT = "constraint"
    AMBIGUITY = "ambiguity"


class TestType(StrEnum):
    """Scenario categories used to balance generated test suites."""

    POSITIVE = "positive"
    NEGATIVE = "negative"
    BOUNDARY = "boundary"
    EDGE = "edge"
    SECURITY = "security"
    PERFORMANCE = "performance"


class Document(StrictModel):
    """Parsed source document, represented as ordered page-like sections."""

    source_path: str
    text: str
    page_texts: list[str] = Field(default_factory=list)


class Chunk(StrictModel):
    """A section-aware PRD excerpt with stable source metadata."""

    chunk_id: str
    text: str
    section_path: str
    page: int | None = None


class RequirementPoint(StrictModel):
    """An atomic statement grounded in a source chunk."""

    id: str
    text: str
    type: RequirementType
    priority: str = "medium"
    chunk_id: str


class RequirementBatch(StrictModel):
    """Structured extractor response."""

    requirements: list[RequirementPoint]


class TestCase(StrictModel):
    """A manually executable scenario linked to one or more requirements."""

    id: str
    req_ids: list[str] = Field(min_length=1)
    title: str
    preconditions: list[str] = Field(default_factory=list)
    steps: list[str] = Field(min_length=1)
    test_data: list[str] = Field(default_factory=list)
    expected: str
    type: TestType
    priority: str = "medium"


class TestCaseBatch(StrictModel):
    """Structured generator response."""

    test_cases: list[TestCase]


class CritiqueIssue(StrictModel):
    """Actionable critic feedback associated with a case or requirement."""

    test_case_id: str | None = None
    requirement_id: str | None = None
    severity: str
    description: str
    suggestion: str


class Critique(StrictModel):
    """Structured scores and feedback for one generated suite version."""

    score: float = Field(ge=0, le=10)
    coverage_score: float = Field(ge=0, le=100)
    correctness: float = Field(ge=0, le=10)
    clarity: float = Field(ge=0, le=10)
    atomicity: float = Field(ge=0, le=10)
    completeness: float = Field(ge=0, le=10)
    traceability: float = Field(ge=0, le=10)
    diversity: float = Field(ge=0, le=10)
    issues: list[CritiqueIssue] = Field(default_factory=list)
    missing_req_ids: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
    hallucination_risks: list[str] = Field(default_factory=list)


class CoverageReport(StrictModel):
    """Deterministic requirement-to-test mapping."""

    covered_requirement_ids: list[str]
    uncovered_requirement_ids: list[str]
    missing_positive_requirement_ids: list[str]
    test_cases_by_requirement: dict[str, list[str]]


class IterationRecord(StrictModel):
    """Append-only audit entry for a generator/critic iteration."""

    iteration: int
    score: float
    coverage_score: float
    test_cases: list[TestCase]
    critique: Critique
