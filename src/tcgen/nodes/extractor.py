"""Requirement extraction and deterministic cross-chunk deduplication."""

from __future__ import annotations

import hashlib
import re

from tcgen.config import AppConfig
from tcgen.llm import Invokable, invoke_structured
from tcgen.models import Chunk, RequirementBatch, RequirementPoint
from tcgen.prompts import render_prompt


def _normalize(text: str) -> str:
    """Normalize punctuation and whitespace for conservative exact deduplication."""
    return re.sub(r"\W+", " ", text.casefold()).strip()


def extract_requirements(
    chunks: list[Chunk], model: Invokable, config: AppConfig
) -> tuple[list[RequirementPoint], int, int]:
    """Extract validated requirement points from each source chunk."""
    points_by_text: dict[str, RequirementPoint] = {}
    input_tokens = 0
    output_tokens = 0
    for chunk in chunks:
        prompt = render_prompt(
            "extractor",
            chunk_id=chunk.chunk_id,
            section_path=chunk.section_path,
            text=chunk.text,
        )
        batch, prompt_count, output_count = invoke_structured(
            model, prompt, RequirementBatch, config.request_retries
        )
        input_tokens += prompt_count
        output_tokens += output_count
        for point in batch.requirements:
            normalized = _normalize(point.text)
            if not normalized:
                continue
            stable_id = "req-" + hashlib.sha1(normalized.encode()).hexdigest()[:10]
            points_by_text.setdefault(
                normalized,
                point.model_copy(update={"id": stable_id, "chunk_id": chunk.chunk_id}),
            )
    return list(points_by_text.values()), input_tokens, output_tokens
