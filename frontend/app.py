"""Streamlit frontend for the local PRD test-case and RAG workflow."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

import streamlit as st
from ollama import ResponseError

from tcgen.config import AppConfig, load_config
from tcgen.graph import create_graph
from tcgen.rag.indexer import index_repository
from tcgen.rag.qa import answer_question

SAMPLE_PRDS: dict[str, str] = {
    "Two-factor authentication": """# Two-factor authentication

## Functional requirement
The service sends a one-time verification code to the user's registered phone
number or email address during login. The verification code expires after 10
minutes and can only be used once.

## Security constraint
The service limits the number of verification-code attempts to prevent
brute-force attacks.
""",
    "Account registration": """# Account registration

## Functional requirement
The service allows a user to create an account using their name, email address,
and password. The service sends a verification link to the provided email
address.

## Security constraint
The service does not activate the account until the email address has been
verified.
""",
    "File upload": """# File upload

## Functional requirement
The service allows authenticated users to upload files up to 10 MB in size.
The service stores uploaded files and associates them with the user's account.

## Security constraint
The service rejects unsupported file types and scans uploaded files for
malicious content.
""",
    "Online payment": """# Online payment

## Functional requirement
The service allows users to make payments using a supported payment method.
The service displays the payment status after the transaction is completed.

## Security constraint
The service does not store users' complete card numbers or CVV information.
""",
    "User login": """# User login

## Functional requirement
The service authenticates users using their registered email address and
password. The service creates a session after successful authentication.

## Security constraint
The service temporarily locks login attempts after multiple consecutive failed
authentication attempts.
""",
}
PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _write_prd(text: str) -> Path:
    """Write editor content to a temporary Markdown file for the graph."""
    handle = tempfile.NamedTemporaryFile(
        mode="w", suffix=".md", prefix="tcgen-", encoding="utf-8", delete=False
    )
    with handle:
        handle.write(text)
    return Path(handle.name)


def _load_settings(config_path: Path) -> AppConfig:
    """Load frontend settings with paths anchored to the project root."""
    resolved_config = config_path if config_path.is_absolute() else PROJECT_ROOT / config_path
    settings = load_config(resolved_config)
    if not settings.chroma_path.is_absolute():
        settings.chroma_path = PROJECT_ROOT / settings.chroma_path
    return settings


def _show_ollama_error(error: ResponseError, model_name: str) -> None:
    """Explain a local Ollama model failure and show the recovery command."""
    message = str(error)
    st.error(f"Ollama request failed: {message}")
    if "not found" in message.casefold():
        st.info(
            "The configured model is not installed locally. Pull it from PowerShell, "
            "then retry:\n\n"
            f"```powershell\nollama pull {model_name}\n```"
        )


def _show_case(case: Any) -> None:
    """Render one generated test case."""
    with st.expander(f"{case.type.value.title()} - {case.title}", expanded=False):
        st.caption(f"{case.id} | priority: {case.priority}")
        st.write("**Requirements:**", ", ".join(case.req_ids))
        if case.preconditions:
            st.write("**Preconditions:**", "; ".join(case.preconditions))
        st.write("**Steps:**")
        for index, step in enumerate(case.steps, start=1):
            st.write(f"{index}. {step}")
        if case.test_data:
            st.write("**Test data:**", "; ".join(case.test_data))
        st.write("**Expected result:**", case.expected)


def _run_generation(prd_text: str, out_dir: Path, config_path: Path) -> dict[str, Any]:
    """Run the graph and stream agent progress into the Streamlit session."""
    settings = _load_settings(config_path)
    graph = create_graph(settings)
    progress = st.empty()
    result: dict[str, Any] = {}
    prd_path = _write_prd(prd_text)
    try:
        initial = {
            "prd_path": str(prd_path),
            "out_dir": str(out_dir),
            "iteration": 0,
            "history": [],
            "stale_iterations": 0,
        }
        for event in graph.stream(initial, stream_mode="updates"):
            for node, update in event.items():
                if not isinstance(update, dict):
                    continue
                result.update(update)
                if node == "critic" and "critique" in update:
                    critique = update["critique"]
                    progress.info(
                        f"Round {result.get('iteration', 0)} complete - "
                        f"quality {critique.score:.1f}/10, "
                        f"coverage {critique.coverage_score:.1f}%"
                    )
                else:
                    progress.info(f"Agent active: {node}")
        progress.success("Generation and review loop completed.")
        return result
    finally:
        prd_path.unlink(missing_ok=True)


def _render_generation(result: dict[str, Any]) -> None:
    """Render generated cases, quality metrics, gaps, and iteration history."""
    critique = result.get("critique")
    coverage = result.get("coverage")
    cases = result.get("test_cases", [])
    if critique:
        columns = st.columns(3)
        columns[0].metric("Quality", f"{critique.score:.1f}/10")
        columns[1].metric("Semantic coverage", f"{critique.coverage_score:.1f}%")
        columns[2].metric("Refinement rounds", str(result.get("iteration", 0)))
        if critique.suggestions:
            suggestions = "\n".join(f"- {item}" for item in critique.suggestions)
            st.warning("Critic suggestions:\n\n" + suggestions)
    if coverage:
        st.subheader("Coverage")
        st.dataframe(
            [
                {
                    "Requirement": requirement_id,
                    "Test cases": ", ".join(case_ids) or "Uncovered",
                    "Positive path": requirement_id
                    not in coverage.missing_positive_requirement_ids,
                }
                for requirement_id, case_ids in coverage.test_cases_by_requirement.items()
            ],
            use_container_width=True,
            hide_index=True,
        )
    st.subheader(f"Generated test cases ({len(cases)})")
    for case in cases:
        _show_case(case)
    gaps = result.get("run_report", {}).get("remaining_gaps", {})
    gap_ids = sorted(
        set(gaps.get("uncovered_requirement_ids", []))
        | set(gaps.get("missing_positive_requirement_ids", []))
        | set(gaps.get("critic_missing_requirement_ids", []))
    )
    if gap_ids:
        st.error("Remaining gaps after the refinement cap")
        st.write(", ".join(gap_ids))
    with st.expander("Agent iteration history"):
        st.json(
            [
                {
                    "iteration": record.iteration,
                    "quality": record.score,
                    "coverage": record.coverage_score,
                    "issues": len(record.critique.issues),
                }
                for record in result.get("history", [])
            ]
        )


def main() -> None:
    """Render the tcgen frontend."""
    st.set_page_config(page_title="tcgen local AI workbench", page_icon="🧪", layout="wide")
    st.title("🧪 tcgen local AI workbench")
    st.caption("PRD → extractor → generator → coverage → critic, with local Ollama and Chroma RAG")

    with st.sidebar:
        st.header("Configuration")
        config_path = Path(
            st.text_input(
                "Config file", value="config.yaml", help="Path relative to the project root."
            )
        )
        st.divider()
        st.header("Repository RAG")
        repository = Path(st.text_input("Repository to index", value="."))
        repository = repository if repository.is_absolute() else PROJECT_ROOT / repository
        settings = _load_settings(config_path)
        if st.button("Index repository", use_container_width=True):
            try:
                with st.spinner("Embedding repository chunks locally with Ollama..."):
                    count = index_repository(repository, settings)
                st.success(f"Indexed {count} chunks.")
            except ResponseError as error:
                _show_ollama_error(error, settings.models["embeddings"].name)
            except (FileNotFoundError, NotADirectoryError, ValueError, ConnectionError) as error:
                st.error(f"Repository indexing failed: {error}")

    generate_tab, rag_tab = st.tabs(["Generate test cases", "Ask the repository"])
    with generate_tab:
        sample_name = st.selectbox("Choose a sample PRD", ["Custom PRD", *SAMPLE_PRDS])
        if sample_name == "Custom PRD":
            uploaded = st.file_uploader("Upload a Markdown or text PRD", type=["md", "txt"])
            default_text = ""
            if uploaded and uploaded.name.lower().endswith((".md", ".txt")):
                default_text = uploaded.getvalue().decode("utf-8", errors="replace")
            prd_text = st.text_area("PRD content", value=default_text, height=320)
        else:
            prd_text = st.text_area("PRD content", value=SAMPLE_PRDS[sample_name], height=320)
        out_dir = Path(st.text_input("Report output folder", value="out"))
        out_dir = out_dir if out_dir.is_absolute() else PROJECT_ROOT / out_dir
        if st.button("Generate and review test cases", type="primary", use_container_width=True):
            if not prd_text.strip():
                st.error("Provide PRD content before starting generation.")
            else:
                with st.spinner("Running local agents..."):
                    result = _run_generation(prd_text, out_dir, config_path)
                st.session_state["last_result"] = result
        if "last_result" in st.session_state:
            _render_generation(st.session_state["last_result"])

    with rag_tab:
        st.subheader("Local repository Q&A")
        st.write(
            "Index the repository from the sidebar, then ask a question. "
            "Answers include source line citations."
        )
        question = st.text_input(
            "Question", placeholder="How does the critic loop decide when to stop?"
        )
        if st.button("Ask RAG", use_container_width=True):
            if not question.strip():
                st.error("Enter a question first.")
            else:
                with st.spinner("Retrieving local source and asking Ollama..."):
                    try:
                        answer = answer_question(question, _load_settings(config_path))
                    except FileNotFoundError:
                        st.warning(
                            "The repository has not been indexed yet. "
                            "Click **Index repository** in the sidebar, wait for it to finish, "
                            "then ask your question again."
                        )
                    except ResponseError as error:
                        _show_ollama_error(
                            error, _load_settings(config_path).models["embeddings"].name
                        )
                    except (ConnectionError, ValueError) as error:
                        st.error(f"RAG request failed: {error}")
                    else:
                        st.markdown(answer)


if __name__ == "__main__":
    main()
