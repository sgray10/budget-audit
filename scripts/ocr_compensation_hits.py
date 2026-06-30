from __future__ import annotations

import csv
import re
from pathlib import Path

TERMS_RE = re.compile(
    r"salary|salaries|wage|wages|overtime|insurance|retirement|social security|medicare|payroll",
    re.IGNORECASE,
)

LINE_RE = re.compile(
    r"^\s*(?P<account>\d{3,5})\s+(?P<label>.*?)\s+"
    r"(?P<actual_24_25>[\d,§().-]+)\s+"
    r"(?P<budget_25_26>[\d,§().-]+)\s+"
    r"(?P<actual_25_26>[\d,§().-]+)\s+"
    r"(?P<budget_26_27>[\d,§().-]+)\s*$"
)

ocr_dir = Path("data/interim/ocr")
out_path = Path("data/processed/compensation_ocr_hits.csv")
out_path.parent.mkdir(parents=True, exist_ok=True)

rows: list[dict[str, str]] = []

for text_path in sorted(ocr_dir.glob("page-*.txt")):
    page_number = int(text_path.stem.removeprefix("page-"))
    for line_number, line in enumerate(text_path.read_text(encoding="utf-8").splitlines(), start=1):
        if not TERMS_RE.search(line):
            continue

        match = LINE_RE.match(line)
        row = {
            "document_id": "weakley-fwm-2026-06-30",
            "page_number": str(page_number),
            "line_number": str(line_number),
            "raw_line": line,
            "account": "",
            "label": "",
            "actual_24_25": "",
            "budget_25_26": "",
            "actual_25_26": "",
            "budget_26_27": "",
            "parse_status": "raw_hit",
        }

        if match:
            row.update(match.groupdict())
            row["parse_status"] = "parsed"

        rows.append(row)

with out_path.open("w", newline="", encoding="utf-8") as handle:
    writer = csv.DictWriter(
        handle,
        fieldnames=[
            "document_id",
            "page_number",
            "line_number",
            "account",
            "label",
            "actual_24_25",
            "budget_25_26",
            "actual_25_26",
            "budget_26_27",
            "parse_status",
            "raw_line",
        ],
    )
    writer.writeheader()
    writer.writerows(rows)

print(f"wrote {out_path} ({len(rows)} rows)")
