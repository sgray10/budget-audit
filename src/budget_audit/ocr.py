from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

import pytesseract  # type: ignore[import-untyped]
from PIL import Image

from budget_audit.render import parse_page_spec


@dataclass(frozen=True)
class OcrPage:
    image_path: Path
    page_number: int
    text_path: Path
    text_char_count: int


def page_number_from_image_path(path: Path) -> int:
    """Extract page number from names like page-023.png."""
    stem = path.stem
    if not stem.startswith("page-"):
        raise ValueError(f"expected image filename like page-023.png: {path}")
    return int(stem.removeprefix("page-"))


def ocr_image(image_path: Path) -> str:
    """OCR one rendered page image."""
    with Image.open(image_path) as image:
        text = pytesseract.image_to_string(image)
        return str(text)


def ocr_rendered_pages(
    rendered_dir: Path,
    out_dir: Path,
    pages: Iterable[int],
) -> list[OcrPage]:
    """OCR selected rendered page PNGs to page-###.txt files."""
    out_dir.mkdir(parents=True, exist_ok=True)
    results: list[OcrPage] = []

    for page_number in pages:
        image_path = rendered_dir / f"page-{page_number:03d}.png"
        if not image_path.exists():
            raise FileNotFoundError(f"missing rendered page image: {image_path}")

        text = ocr_image(image_path)
        text_path = out_dir / f"page-{page_number:03d}.txt"
        text_path.write_text(text, encoding="utf-8")

        results.append(
            OcrPage(
                image_path=image_path,
                page_number=page_number,
                text_path=text_path,
                text_char_count=len(text),
            )
        )

    return results


__all__ = [
    "OcrPage",
    "ocr_image",
    "ocr_rendered_pages",
    "page_number_from_image_path",
    "parse_page_spec",
]
