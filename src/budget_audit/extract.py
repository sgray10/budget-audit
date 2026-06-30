from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
import hashlib
from pathlib import Path

import pdfplumber


@dataclass(frozen=True)
class ExtractedTable:
    source_path: Path
    page_number: int
    table_index: int
    rows: list[list[str | None]]
    extraction_method: str = "pdfplumber"


@dataclass(frozen=True)
class PageInspection:
    source_path: Path
    page_number: int
    has_text_layer: bool
    text_char_count: int
    likely_table: bool


def sha256_file(path: Path) -> str:
    """Return the SHA-256 digest for a source file."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def inspect_pdf(path: Path) -> list[PageInspection]:
    """Inspect a PDF and return basic page-level metadata."""
    inspections: list[PageInspection] = []
    with pdfplumber.open(path) as pdf:
        for idx, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            tables = page.extract_tables() or []
            inspections.append(
                PageInspection(
                    source_path=path,
                    page_number=idx,
                    has_text_layer=bool(text.strip()),
                    text_char_count=len(text),
                    likely_table=bool(tables),
                )
            )
    return inspections


def extract_tables(path: Path, pages: Iterable[int] | None = None) -> list[ExtractedTable]:
    """Extract tables from a PDF using pdfplumber.

    This is the first-pass extractor. Scanned pages and hard cases will need OCR
    or manual review.
    """
    selected_pages = set(pages) if pages is not None else None
    extracted: list[ExtractedTable] = []

    with pdfplumber.open(path) as pdf:
        for idx, page in enumerate(pdf.pages, start=1):
            if selected_pages is not None and idx not in selected_pages:
                continue
            for table_index, table in enumerate(page.extract_tables() or [], start=1):
                extracted.append(
                    ExtractedTable(
                        source_path=path,
                        page_number=idx,
                        table_index=table_index,
                        rows=table,
                    )
                )
    return extracted
