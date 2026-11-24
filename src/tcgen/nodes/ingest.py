"""Document parsers for supported PRD formats."""

from __future__ import annotations

import re
from pathlib import Path

from docx import Document as DocxDocument
from docx.table import Table
from docx.text.paragraph import Paragraph
from pypdf import PdfReader

from tcgen.models import Document


def _read_docx(path: Path) -> str:
    """Read DOCX paragraphs and tables in their original body order."""
    doc = DocxDocument(str(path))
    blocks: list[str] = []
    for child in doc.element.body.iterchildren():
        if child.tag.endswith("}p"):
            paragraph = Paragraph(child, doc)
            if paragraph.text:
                style_name = paragraph.style.name if paragraph.style else ""
                heading = re.fullmatch(r"Heading\s+(\d+)", style_name, re.IGNORECASE)
                if heading:
                    level = min(int(heading.group(1)), 6)
                    blocks.append(f"{'#' * level} {paragraph.text}")
                else:
                    blocks.append(paragraph.text)
        elif child.tag.endswith("}tbl"):
            table = Table(child, doc)
            blocks.extend(
                "| " + " | ".join(cell.text.replace("\n", " ") for cell in row.cells) + " |"
                for row in table.rows
            )
    return "\n\n".join(blocks)


def parse_document(path: Path) -> Document:
    """Parse PDF, DOCX, Markdown, or plain text while retaining page boundaries."""
    if not path.is_file():
        raise FileNotFoundError(f"PRD file does not exist: {path}")
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        pages = [page.extract_text() or "" for page in PdfReader(str(path)).pages]
        page_texts = pages
    elif suffix == ".docx":
        pages = [_read_docx(path)]
        page_texts = []
    elif suffix in {".md", ".txt"}:
        pages = [path.read_text(encoding="utf-8-sig")]
        page_texts = []
    else:
        raise ValueError(f"Unsupported PRD format {suffix!r}; use PDF, DOCX, MD, or TXT")
    text = "\n\n".join(page for page in pages if page.strip())
    if not text.strip():
        raise ValueError(f"No extractable text found in PRD: {path}")
    return Document(source_path=str(path.resolve()), text=text, page_texts=page_texts)
