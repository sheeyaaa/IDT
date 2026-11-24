"""LangGraph assembly for the local PRD-to-test-case workflow."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from langgraph.graph import END, START, StateGraph

from tcgen.config import AppConfig
from tcgen.llm import Invokable, create_model_clients
from tcgen.models import IterationRecord
from tcgen.nodes.chunker import chunk_document
from tcgen.nodes.coverage import check_coverage
from tcgen.nodes.critic import critique_suite
from tcgen.nodes.exporter import export_suite
from tcgen.nodes.extractor import extract_requirements
from tcgen.nodes.generator import generate_test_cases
from tcgen.nodes.ingest import parse_document
from tcgen.state import GraphState


def create_graph(config: AppConfig, clients: dict[str, Invokable] | None = None) -> Any:
    """Build a compiled graph, optionally using injected test model clients."""
    model_clients = clients or create_model_clients(config)

    def ingest(state: GraphState) -> dict[str, Any]:
        started_at = state.get("started_at", time.monotonic())
        document = parse_document(Path(state["prd_path"]))
        return {
            "document": document,
            "started_at": started_at,
            "token_stats": state.get("token_stats", {"input_tokens": 0, "output_tokens": 0}),
            "config": config.model_dump(mode="json"),
        }

    def chunker(state: GraphState) -> dict[str, Any]:
        return {
            "chunks": chunk_document(
                state["document"], config.chunk_size_tokens, config.chunk_overlap_tokens
            )
        }

    def extractor(state: GraphState) -> dict[str, Any]:
        points, input_tokens, output_tokens = extract_requirements(
            state["chunks"], model_clients["extractor"], config
        )
        totals = state["token_stats"]
        return {
            "requirement_points": points,
            "token_stats": {
                "input_tokens": totals["input_tokens"] + input_tokens,
                "output_tokens": totals["output_tokens"] + output_tokens,
            },
        }

    def generator(state: GraphState) -> dict[str, Any]:
        cases, input_tokens, output_tokens = generate_test_cases(
            state["requirement_points"],
            state.get("test_cases", []),
            state.get("critique"),
            model_clients["generator"],
            config,
        )
        totals = state["token_stats"]
        return {
            "test_cases": cases,
            "iteration": state.get("iteration", 0) + 1,
            "token_stats": {
                "input_tokens": totals["input_tokens"] + input_tokens,
                "output_tokens": totals["output_tokens"] + output_tokens,
            },
        }

    def coverage_checker(state: GraphState) -> dict[str, Any]:
        return {"coverage": check_coverage(state["requirement_points"], state["test_cases"])}

    def critic(state: GraphState) -> dict[str, Any]:
        result, input_tokens, output_tokens = critique_suite(
            state["requirement_points"],
            state["test_cases"],
            state["coverage"],
            model_clients["critic"],
            config,
        )
        deterministic_missing = list(
            dict.fromkeys(
                state["coverage"].uncovered_requirement_ids
                + state["coverage"].missing_positive_requirement_ids
            )
        )
        if deterministic_missing:
            result = result.model_copy(
                update={
                    "missing_req_ids": list(
                        dict.fromkeys(result.missing_req_ids + deterministic_missing)
                    )
                }
            )
        previous_scores = [record.score for record in state.get("history", [])]
        best_previous = max(previous_scores, default=-1.0)
        stale = state.get("stale_iterations", 0) + 1 if result.score <= best_previous else 0
        history = state.get("history", []) + [
            IterationRecord(
                iteration=state["iteration"],
                score=result.score,
                coverage_score=result.coverage_score,
                test_cases=state["test_cases"],
                critique=result,
            )
        ]
        totals = state["token_stats"]
        return {
            "critique": result,
            "history": history,
            "stale_iterations": stale,
            "token_stats": {
                "input_tokens": totals["input_tokens"] + input_tokens,
                "output_tokens": totals["output_tokens"] + output_tokens,
            },
        }

    def route(state: GraphState) -> str:
        """Apply quality, coverage, no-improvement, and hard iteration stops."""
        critique_result = state["critique"]
        if (
            critique_result.score >= config.quality_threshold
            and critique_result.coverage_score >= config.coverage_target
        ):
            return "exporter"
        if state["iteration"] >= config.max_iterations:
            return "exporter"
        if state.get("stale_iterations", 0) >= 2:
            return "exporter"
        return "generator"

    def exporter(state: GraphState) -> dict[str, Any]:
        elapsed = time.monotonic() - state["started_at"]
        report: dict[str, Any] = {
            "source_path": state["document"].source_path,
            "models": {role: setting.name for role, setting in config.models.items()},
            "iterations": state["iteration"],
            "final_quality_score": state["critique"].score,
            "final_coverage_score": state["critique"].coverage_score,
            "deterministic_coverage_percent": (
                100
                * len(state["coverage"].covered_requirement_ids)
                / max(1, len(state["requirement_points"]))
            ),
            "remaining_gaps": {
                "uncovered_requirement_ids": state["coverage"].uncovered_requirement_ids,
                "missing_positive_requirement_ids": (
                    state["coverage"].missing_positive_requirement_ids
                ),
                "critic_missing_requirement_ids": state["critique"].missing_req_ids,
            },
            "requirement_count": len(state["requirement_points"]),
            "test_case_count": len(state["test_cases"]),
            "elapsed_seconds": round(elapsed, 3),
            "estimated_token_counts": state["token_stats"],
            "token_count_note": (
                "Estimated as characters divided by four; Ollama token usage is not "
                "consistently available."
            ),
        }
        export_suite(
            Path(state["out_dir"]),
            state["requirement_points"],
            state["test_cases"],
            state["coverage"],
            state["critique"],
            report,
            state.get("history", []),
        )
        return {"elapsed_seconds": elapsed, "run_report": report}

    graph = StateGraph(GraphState)
    graph.add_node("ingest", ingest)
    graph.add_node("chunker", chunker)
    graph.add_node("extractor", extractor)
    graph.add_node("generator", generator)
    graph.add_node("coverage_checker", coverage_checker)
    graph.add_node("critic", critic)
    graph.add_node("exporter", exporter)
    graph.add_edge(START, "ingest")
    graph.add_edge("ingest", "chunker")
    graph.add_edge("chunker", "extractor")
    graph.add_edge("extractor", "generator")
    graph.add_edge("generator", "coverage_checker")
    graph.add_edge("coverage_checker", "critic")
    graph.add_conditional_edges("critic", route, {"generator": "generator", "exporter": "exporter"})
    graph.add_edge("exporter", END)
    return graph.compile()
