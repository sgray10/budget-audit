from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

import pypdfium2 as pdfium  # type: ignore[import-untyped]


@dataclass(frozen=True)
class RenderedPage:
    source_path: Path
    page_number: int
    image_path: Path
    dpi: int


def render_pdf_pages(
    pdf_path: Path,
    out_dir: Path,
    pages: Iterable[int],
    dpi: int = 200,
) -> list[RenderedPage]:
    """Render selected 1-based PDF pages to PNG files."""
    out_dir.mkdir(parents=True, exist_ok=True)
    rendered: list[RenderedPage] = []

    pdf = pdfium.PdfDocument(str(pdf_path))
    scale = dpi / 72

    for page_number in pages:
        if page_number < 1 or page_number > len(pdf):
            raise ValueError(f"page {page_number} out of range 1-{len(pdf)}")

        page = pdf[page_number - 1]
        image = page.render(scale=scale).to_pil()

        out_path = out_dir / f"page-{page_number:03d}.png"
        image.save(out_path)

        rendered.append(
            RenderedPage(
                source_path=pdf_path,
                page_number=page_number,
                image_path=out_path,
                dpi=dpi,
            )
        )

    return rendered


def parse_page_spec(spec: str) -> list[int]:
    """Parse a page spec like '1,3,5-7' into sorted 1-based page numbers."""
    pages: set[int] = set()

    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue

        if "-" in part:
            start_text, end_text = part.split("-", 1)
            start = int(start_text)
            end = int(end_text)
            if end < start:
                raise ValueError(f"invalid page range: {part}")
            pages.update(range(start, end + 1))
        else:
            pages.add(int(part))

    if not pages:
        raise ValueError("page spec did not include any pages")

    return sorted(pages)
