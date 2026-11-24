"""Language-aware repository chunking and local Chroma persistence."""

from __future__ import annotations

import hashlib
from pathlib import Path

from langchain_chroma import Chroma
from langchain_core.documents import Document as LCDocument
from langchain_ollama import OllamaEmbeddings
from langchain_text_splitters import Language, RecursiveCharacterTextSplitter

from tcgen.config import AppConfig

SUPPORTED_SUFFIXES = {
    ".py",
    ".md",
    ".rst",
    ".txt",
    ".toml",
    ".yaml",
    ".yml",
    ".json",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".go",
    ".java",
    ".html",
    ".css",
    ".sh",
}
EXCLUDED_PARTS = {
    ".git",
    ".venv",
    ".venv1",
    "venv",
    "node_modules",
    "__pycache__",
    ".mypy_cache",
    ".ruff_cache",
    ".pytest_cache",
    ".tcgen",
    "dist",
    "build",
}
LANGUAGES = {
    ".py": Language.PYTHON,
    ".js": Language.JS,
    ".jsx": Language.JS,
    ".ts": Language.TS,
    ".tsx": Language.TS,
    ".go": Language.GO,
    ".java": Language.JAVA,
    ".html": Language.HTML,
    ".md": Language.MARKDOWN,
}


def _embeddings(config: AppConfig) -> OllamaEmbeddings:
    """Create the local embedding client for the configured role."""
    return OllamaEmbeddings(
        model=config.models["embeddings"].name,
        base_url=config.ollama_base_url,
        keep_alive=config.keep_alive,
    )


def _split_file(path: Path, root: Path) -> list[LCDocument]:
    """Create language-aware chunks annotated with one-based source lines."""
    source = path.read_text(encoding="utf-8", errors="replace")
    language = LANGUAGES.get(path.suffix.lower())
    splitter = (
        RecursiveCharacterTextSplitter.from_language(
            language=language,
            chunk_size=2200,
            chunk_overlap=250,
            add_start_index=True,
        )
        if language
        else RecursiveCharacterTextSplitter(
            chunk_size=2200, chunk_overlap=250, add_start_index=True
        )
    )
    relative_path = path.relative_to(root).as_posix()
    result: list[LCDocument] = []
    for part in splitter.create_documents([source]):
        start = int(part.metadata.get("start_index", 0))
        start_line = source.count("\n", 0, start) + 1
        end_line = start_line + part.page_content.count("\n")
        result.append(
            LCDocument(
                page_content=part.page_content,
                metadata={
                    "source": relative_path,
                    "repository": str(root),
                    "start_line": start_line,
                    "end_line": end_line,
                },
            )
        )
    return result


def index_repository(root: Path, config: AppConfig) -> int:
    """Index text and source files into the on-disk local Chroma collection."""
    root = root.resolve()
    if not root.is_dir():
        raise NotADirectoryError(f"Repository directory does not exist: {root}")
    documents: list[LCDocument] = []
    for path in sorted(root.rglob("*")):
        if (
            not path.is_file()
            or path.suffix.lower() not in SUPPORTED_SUFFIXES
            or EXCLUDED_PARTS.intersection(path.relative_to(root).parts)
            or path.stat().st_size > 1_000_000
        ):
            continue
        documents.extend(_split_file(path, root))
    if not documents:
        raise ValueError(f"No supported text/source files were found beneath {root}")
    config.chroma_path.parent.mkdir(parents=True, exist_ok=True)
    store = Chroma(
        collection_name="tcgen_repository",
        persist_directory=str(config.chroma_path),
        embedding_function=_embeddings(config),
    )
    store.delete(where={"repository": str(root)})
    ids = [
        "src-"
        + hashlib.sha1(
            f"{item.metadata['source']}:{item.metadata['start_line']}:{item.page_content}".encode()
        ).hexdigest()
        for item in documents
    ]
    store.add_documents(documents, ids=ids)
    return len(documents)


def retrieve_sources(
    question: str, config: AppConfig, k: int = 5, root: Path = Path(".")
) -> list[LCDocument]:
    """Retrieve repository excerpts from the persistent local vector store."""
    if not config.chroma_path.exists():
        raise FileNotFoundError(
            f"RAG index not found at {config.chroma_path}; run 'tcgen index' first"
        )
    store = Chroma(
        collection_name="tcgen_repository",
        persist_directory=str(config.chroma_path),
        embedding_function=_embeddings(config),
    )
    return store.similarity_search(question, k=k, filter={"repository": str(root.resolve())})
