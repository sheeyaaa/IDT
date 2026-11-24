"""Section-aware chunking with approximate token limits and overlap."""

from __future__ import annotations

import hashlib
import re

from tcgen.models import Chunk, Document

HEADING = re.compile(r"^\s{0,3}(?:#{1,6}\s+.+|\d+(?:\.\d+)*[.)]?\s+.+)\s*$")


def _heading_depth(line: str) -> int:
    """Return a markdown or numbered heading depth."""
    stripped = line.strip()
    if stripped.startswith("#"):
        return len(stripped) - len(stripped.lstrip("#"))
    numbered = re.match(r"^(\d+(?:\.\d+)*)[.)]?\s+", stripped)
    return numbered.group(1).count(".") + 1 if numbered else 1


def _split_oversized(unit: str, max_chars: int) -> list[str]:
    """Split prose that exceeds the limit; intact table/list groups are preferred."""
    if len(unit) <= max_chars or unit.lstrip().startswith("|"):
        return [unit]
    words = unit.split()
    result: list[str] = []
    part = ""
    for word in words:
        if part and len(part) + len(word) + 1 > max_chars:
            result.append(part)
            part = ""
        part = f"{part} {word}".strip()
    if part:
        result.append(part)
    return result


def chunk_document(
    document: Document, chunk_size_tokens: int = 800, overlap_tokens: int = 100
) -> list[Chunk]:
    """Split a parsed PRD by heading sections with a bounded rolling overlap."""
    max_chars = chunk_size_tokens * 4
    overlap_chars = overlap_tokens * 4
    pages = document.page_texts or [document.text]
    chunks: list[Chunk] = []
    for page_number, page_text in enumerate(pages, start=1):
        heading_stack: list[str] = []
        section_path = "Document"
        section_groups: list[str] = []
        page_metadata = page_number if document.page_texts else None

        def flush(
            groups_source: list[str],
            current_page_number: int | None,
            current_section_path: str,
        ) -> None:
            if not groups_source:
                return
            groups = [
                piece
                for group in groups_source
                for piece in _split_oversized(group, max_chars)
                if piece.strip()
            ]
            if not groups:
                return
            current: list[str] = []
            current_chars = 0
            for group in groups:
                if current and current_chars + len(group) + 2 > max_chars:
                    text = "\n\n".join(current)
                    digest = hashlib.sha1(
                        f"{current_page_number}:{current_section_path}:{text}".encode()
                    ).hexdigest()[:10]
                    chunks.append(
                        Chunk(
                            chunk_id=f"chunk-{digest}",
                            text=text,
                            section_path=current_section_path,
                            page=current_page_number,
                        )
                    )
                    carry: list[str] = []
                    carry_chars = 0
                    for previous in reversed(current):
                        if carry_chars + len(previous) + 2 > overlap_chars:
                            break
                        carry.insert(0, previous)
                        carry_chars += len(previous) + 2
                    current = carry
                    current_chars = carry_chars
                current.append(group)
                current_chars += len(group) + 2
            if current:
                text = "\n\n".join(current)
                digest = hashlib.sha1(
                    f"{current_page_number}:{current_section_path}:{text}".encode()
                ).hexdigest()[:10]
                chunks.append(
                    Chunk(
                        chunk_id=f"chunk-{digest}",
                        text=text,
                        section_path=current_section_path,
                        page=current_page_number,
                    )
                )

        for line in page_text.splitlines():
            if HEADING.match(line):
                flush(section_groups, page_metadata, section_path)
                heading = re.sub(r"^\s*#+\s*", "", line).strip()
                depth = _heading_depth(line)
                heading_stack = heading_stack[: depth - 1] + [heading]
                section_path = " / ".join(["Document", *heading_stack])
                section_groups = []
            else:
                section_groups.append(line)
        flush(section_groups, page_metadata, section_path)
    return chunks
