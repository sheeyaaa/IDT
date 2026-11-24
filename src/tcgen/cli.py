"""Typer command-line interface for generation and local repository Q&A."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Annotated

import typer

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tcgen.config import load_config
from tcgen.evaluation import compare_runs
from tcgen.graph import create_graph
from tcgen.rag.indexer import index_repository
from tcgen.rag.qa import answer_question, evaluate_retrieval

app = typer.Typer(
    name="tcgen",
    help="Generate traceable test cases from PRDs using local Ollama models.",
    no_args_is_help=True,
    add_completion=False,
)


@app.command()
def run(
    prd: Annotated[Path, typer.Option("--prd", exists=True, readable=True)],
    out: Annotated[Path, typer.Option("--out")],
    config: Annotated[Path, typer.Option("--config")] = Path("config.yaml"),
    no_color: Annotated[bool, typer.Option("--no-color")] = False,
) -> None:
    """Parse a PRD, generate and review test cases, and export reports."""
    del no_color
    settings = load_config(config)
    graph = create_graph(settings)
    result: dict[str, object] = {}
    initial = {
        "prd_path": str(prd),
        "out_dir": str(out),
        "iteration": 0,
        "history": [],
        "stale_iterations": 0,
    }
    for event in graph.stream(initial, stream_mode="updates"):
        for node, update in event.items():
            if isinstance(update, dict):
                result.update(update)
                if node == "critic" and "critique" in update:
                    critique = update["critique"]
                    typer.echo(
                        f"Iteration {result.get('iteration', 0)}: "
                        f"quality {critique.score:.1f}/10, "
                        f"coverage {critique.coverage_score:.1f}%"
                    )
    report = result.get("run_report", {})
    typer.echo(f"Reports written to {out.resolve()}")
    typer.echo(json.dumps(report, indent=2))


@app.command()
def index(
    repository: Annotated[Path, typer.Argument()] = Path("."),
    config: Annotated[Path, typer.Option("--config")] = Path("config.yaml"),
) -> None:
    """Index repository source and documentation into the local Chroma database."""
    count = index_repository(repository, load_config(config))
    typer.echo(f"Indexed {count} chunks from {repository.resolve()}")


@app.command()
def ask(
    question: Annotated[str, typer.Argument()],
    config: Annotated[Path, typer.Option("--config")] = Path("config.yaml"),
) -> None:
    """Answer a repository question with source file and line citations."""
    typer.echo(answer_question(question, load_config(config)))


@app.command("eval-rag")
def eval_rag(
    dataset: Annotated[Path, typer.Option("--dataset", exists=True, readable=True)] = Path(
        "tests/data/rag_eval.json"
    ),
    config: Annotated[Path, typer.Option("--config")] = Path("config.yaml"),
) -> None:
    """Report the source-file retrieval hit rate for the checked-in evaluation set."""
    result = evaluate_retrieval(dataset, load_config(config))
    typer.echo(json.dumps(result, indent=2))


@app.command("compare")
def compare(
    single_pass: Annotated[Path, typer.Option("--single-pass", exists=True, readable=True)],
    critic_loop: Annotated[Path, typer.Option("--critic-loop", exists=True, readable=True)],
    out: Annotated[Path, typer.Option("--out")],
) -> None:
    """Compare saved single-pass and critic-loop suite reports."""
    typer.echo(json.dumps(compare_runs(single_pass, critic_loop, out), indent=2))


def main() -> None:
    """Run the CLI application."""
    app()


if __name__ == "__main__":
    main()
