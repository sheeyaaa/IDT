"""Repository Q&A and retrieval evaluation using only local Ollama models."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from langchain_ollama import ChatOllama

from tcgen.config import AppConfig
from tcgen.llm import unload_model
from tcgen.prompts import render_prompt
from tcgen.rag.indexer import retrieve_sources


def answer_question(question: str, config: AppConfig, k: int = 5) -> str:
    """Answer a repository question and append exact source line citations."""
    documents = retrieve_sources(question, config, k=k)
    unload_model(
        config.models["embeddings"].name,
        config.ollama_base_url,
    )
    context = "\n\n".join(
        f"[{doc.metadata['source']}:L{doc.metadata['start_line']}-"
        f"L{doc.metadata['end_line']}]\n{doc.page_content}"
        for doc in documents
    )
    prompt = render_prompt("rag_qa", context=context, question=question)
    settings = config.models["generator"]
    model = ChatOllama(
        model=settings.name,
        base_url=config.ollama_base_url,
        temperature=settings.temperature,
        keep_alive=config.keep_alive,
    )
    response = model.invoke(prompt)
    citations = "\n".join(
        f"- [{doc.metadata['source']}:L{doc.metadata['start_line']}-L{doc.metadata['end_line']}]"
        for doc in documents
    )
    answer = str(response.content)
    return f"{answer}\n\nSources:\n{citations}" if citations else answer


def evaluate_retrieval(dataset_path: Path, config: AppConfig, k: int = 5) -> dict[str, Any]:
    """Measure hit rate when any expected source file appears in retrieved results."""
    cases = json.loads(dataset_path.read_text(encoding="utf-8"))
    if not isinstance(cases, list) or not cases:
        raise ValueError("RAG evaluation data must be a non-empty JSON array")
    hits = 0
    details: list[dict[str, Any]] = []
    for case in cases:
        question = str(case["question"])
        expected_sources = {source.casefold() for source in case["expected_sources"]}
        retrieved = retrieve_sources(question, config, k=k)
        sources = [str(doc.metadata["source"]) for doc in retrieved]
        hit = any(
            expected in source.casefold() for source in sources for expected in expected_sources
        )
        hits += int(hit)
        details.append({"question": question, "hit": hit, "sources": sources})
    return {"hit_rate": hits / len(cases), "hits": hits, "total": len(cases), "details": details}
