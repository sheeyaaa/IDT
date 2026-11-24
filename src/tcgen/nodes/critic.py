"""Structured quality, semantic coverage, and hallucination review."""

from __future__ import annotations

import json

from tcgen.config import AppConfig
from tcgen.llm import Invokable, invoke_structured
from tcgen.models import CoverageReport, Critique, RequirementPoint, TestCase
from tcgen.prompts import render_prompt


def critique_suite(
    requirements: list[RequirementPoint],
    cases: list[TestCase],
    coverage: CoverageReport,
    model: Invokable,
    config: AppConfig,
) -> tuple[Critique, int, int]:
    """Review groundedness, scenario quality, and deterministic plus semantic coverage."""
    prompt = render_prompt(
        "critic",
        requirements=json.dumps([item.model_dump(mode="json") for item in requirements], indent=2),
        test_cases=json.dumps([item.model_dump(mode="json") for item in cases], indent=2),
        coverage=json.dumps(coverage.model_dump(mode="json"), indent=2),
    )
    result, input_tokens, output_tokens = invoke_structured(
        model, prompt, Critique, config.request_retries
    )
    known_ids = {item.id for item in requirements}
    invalid_missing = set(result.missing_req_ids) - known_ids
    if invalid_missing:
        raise ValueError(f"Critic referenced unknown requirements: {sorted(invalid_missing)}")
    return result, input_tokens, output_tokens
