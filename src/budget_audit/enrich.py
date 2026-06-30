from __future__ import annotations

import csv
from pathlib import Path


PAGE_REVIEW_FIELDS = [
    "section_hint",
    "page_type",
    "fund_number",
    "fund_name",
    "department",
    "division",
    "contains_budget_table",
    "contains_salary_or_compensation",
    "review_confidence",
]


def enrich_ocr_rows_with_page_review(
    rows_path: Path,
    page_review_path: Path,
    out_path: Path,
) -> int:
    review_rows = list(csv.DictReader(page_review_path.open(encoding="utf-8")))
    review_by_page = {row["page_number"]: row for row in review_rows}

    ocr_rows = list(csv.DictReader(rows_path.open(encoding="utf-8")))
    if not ocr_rows:
        raise ValueError(f"no OCR rows found in {rows_path}")

    fieldnames = list(ocr_rows[0].keys())
    for field in PAGE_REVIEW_FIELDS:
        if field not in fieldnames:
            fieldnames.insert(4, field)

    enriched: list[dict[str, str]] = []

    for row in ocr_rows:
        page_key = str(int(row["page_number"]))
        review = review_by_page.get(page_key, {})

        new_row = dict(row)
        for field in PAGE_REVIEW_FIELDS:
            new_row[field] = review.get(field, "")

        enriched.append(new_row)

    out_path.parent.mkdir(parents=True, exist_ok=True)

    with out_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(enriched)

    return len(enriched)
