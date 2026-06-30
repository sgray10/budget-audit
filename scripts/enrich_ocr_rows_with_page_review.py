from __future__ import annotations

import csv
from pathlib import Path

rows_path = Path("data/processed/ocr_table_rows.csv")
review_path = Path("review/weakley-fwm-2026-06-30/page_review_023_080.csv")
out_path = Path("data/processed/ocr_table_rows_enriched.csv")

review_rows = list(csv.DictReader(review_path.open(encoding="utf-8")))
review_by_page = {row["page_number"]: row for row in review_rows}

ocr_rows = list(csv.DictReader(rows_path.open(encoding="utf-8")))

extra_fields = [
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

fieldnames = list(ocr_rows[0].keys())
for field in extra_fields:
    if field not in fieldnames:
        fieldnames.insert(4, field)

enriched = []

for row in ocr_rows:
    page_key = str(int(row["page_number"]))
    review = review_by_page.get(page_key, {})

    new_row = dict(row)
    for field in extra_fields:
        new_row[field] = review.get(field, "")

    enriched.append(new_row)

with out_path.open("w", newline="", encoding="utf-8") as handle:
    writer = csv.DictWriter(handle, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(enriched)

print(f"wrote {out_path} ({len(enriched)} rows)")
