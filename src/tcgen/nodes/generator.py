"""Batched test generation and selective critic-driven revisions."""

from __future__ import annotations

import hashlib
import json
import re

from tcgen.config import AppConfig
from tcgen.llm import Invokable, invoke_structured
from tcgen.models import Critique, RequirementPoint, TestCase, TestCaseBatch
from tcgen.prompts import render_prompt


def _case_id(case: TestCase) -> str:
    """Create a stable case ID from its linked requirements, type, and title."""
    material = "|".join(
        [",".join(sorted(case.req_ids)), case.type.value, case.title.casefold().strip()]
    )
    slug = re.sub(r"[^a-z0-9]+", "-", case.title.casefold()).strip("-")[:32] or "case"
    return f"tc-{slug}-{hashlib.sha1(material.encode()).hexdigest()[:8]}"


def generate_test_cases(
    requirements: list[RequirementPoint],
    previous_cases: list[TestCase],
    critique: Critique | None,
    model: Invokable,
    config: AppConfig,
) -> tuple[list[TestCase], int, int]:
    """Generate first-pass cases or update only critic-flagged cases."""
    if not requirements:
        return previous_cases, 0, 0

    existing = {case.id: case for case in previous_cases}
    issues = critique.issues if critique else []
    flagged_ids = {issue.test_case_id for issue in issues if issue.test_case_id}
    missing_ids = set(critique.missing_req_ids if critique else [])
    if critique:
        missing_ids.update(
            point.id
            for point in requirements
            if not any(point.id in case.req_ids for case in previous_cases)
        )
        selected = [
            point
            for point in requirements
            if point.id in missing_ids
            or any(point.id in existing[cid].req_ids for cid in flagged_ids if cid in existing)
        ]
        if not selected:
            return previous_cases, 0, 0
    else:
        selected = requirements

    replacements: dict[str, TestCase] = {}
    input_tokens = 0
    output_tokens = 0
    batch_size = config.generation_batch_size
    for offset in range(0, len(selected), batch_size):
        group = selected[offset : offset + batch_size]
        allowed_ids = {point.id for point in group}
        relevant_cases = [
            case
            for case in previous_cases
            if case.id in flagged_ids and allowed_ids.intersection(case.req_ids)
        ]
        prompt = render_prompt(
            "generator",
            requirements=json.dumps([point.model_dump(mode="json") for point in group], indent=2),
            positive_requirement_ids=json.dumps(sorted(allowed_ids)),
            existing_cases=json.dumps(
                [case.model_dump(mode="json") for case in relevant_cases], indent=2
            ),
            critique=json.dumps(critique.model_dump(mode="json"), indent=2) if critique else "null",
        )
        batch, prompt_count, output_count = invoke_structured(
            model, prompt, TestCaseBatch, config.request_retries
        )
        input_tokens += prompt_count
        output_tokens += output_count
        for case in batch.test_cases:
            if not set(case.req_ids).issubset(allowed_ids):
                raise ValueError(f"Generated case {case.id} references an out-of-batch requirement")
            normalized = case.model_copy(update={"id": _case_id(case)})
            replacements[normalized.id] = normalized
            for old_id in flagged_ids:
                old = existing.get(old_id)
                if old and set(old.req_ids).intersection(normalized.req_ids):
                    existing.pop(old_id, None)
    existing.update(replacements)
    result = list(existing.values())
    return result, input_tokens, output_tokens
