"""Comparison utilities for single-pass and critic-loop run reports."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class RunMetrics(BaseModel):
    """Metrics required to compare one generated suite."""

    model_config = ConfigDict(extra="ignore")

    iterations: int = Field(ge=1, le=5)
    final_quality_score: float = Field(ge=0, le=10)
    final_coverage_score: float = Field(ge=0, le=100)
    test_case_count: int = Field(ge=0)
    elapsed_seconds: float = Field(ge=0)


def _read_metrics(path: Path) -> RunMetrics:
    """Read and validate the run report embedded in a suite JSON file."""
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("run_report"), dict):
        raise ValueError(f"Suite file has no run_report mapping: {path}")
    return RunMetrics.model_validate(data["run_report"])


def compare_runs(single_pass: Path, critic_loop: Path, output: Path) -> dict[str, object]:
    """Write a JSON ablation report showing critic-loop deltas from one-pass output."""
    baseline = _read_metrics(single_pass)
    refined = _read_metrics(critic_loop)
    report: dict[str, object] = {
        "single_pass": baseline.model_dump(mode="json"),
        "critic_loop": refined.model_dump(mode="json"),
        "delta_critic_loop_minus_single_pass": {
            "quality_score": round(refined.final_quality_score - baseline.final_quality_score, 3),
            "coverage_score": round(
                refined.final_coverage_score - baseline.final_coverage_score, 3
            ),
            "test_case_count": refined.test_case_count - baseline.test_case_count,
            "elapsed_seconds": round(refined.elapsed_seconds - baseline.elapsed_seconds, 3),
        },
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report
