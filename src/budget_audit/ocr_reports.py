from __future__ import annotations

import csv
import re
from pathlib import Path

COMPENSATION_TERMS_RE = re.compile(
    r"salary|salaries|wage|wages|overtime|insurance|retirement|social security|medicare|payroll",
    re.IGNORECASE,
)

LINE_RE = re.compile(
    r"^\s*(?P<account>\d{3,5})\s+(?P<label>.*?)\s+"
    r"(?P<actual_24_25>[\d,§,().-]+(?:\s+[\d,§,().-]+)*)\s+"
    r"(?P<budget_25_26>[\d,§,().-]+(?:\s+[\d,§,().-]+)*)\s+"
    r"(?P<actual_25_26>[\d,§,().-]+(?:\s+[\d,§,().-]+)*)\s+"
    r"(?P<budget_26_27>[\d,§,().-]+(?:\s+[\d,§,().-]+)*)\s*$"
)


def clean_ocr_amount(value: str) -> str:
    cleaned = value.replace("§", "5")
    cleaned = re.sub(r"\s+", "", cleaned)
    return cleaned


def find_compensation_hits(
    ocr_dir: Path,
    out_path: Path,
    document_id: str,
) -> int:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, str]] = []

    for text_path in sorted(ocr_dir.glob("page-*.txt")):
        page_number = int(text_path.stem.removeprefix("page-"))
        text = text_path.read_text(encoding="utf-8")

        for line_number, line in enumerate(text.splitlines(), start=1):
            if not COMPENSATION_TERMS_RE.search(line):
                continue

            match = LINE_RE.match(line)
            row = {
                "document_id": document_id,
                "page_number": str(page_number),
                "line_number": str(line_number),
                "account": "",
                "label": "",
                "actual_24_25": "",
                "budget_25_26": "",
                "actual_25_26": "",
                "budget_26_27": "",
                "parse_status": "raw_hit",
                "raw_line": line,
            }

            if match:
                parsed = match.groupdict()
                for amount_field in [
                    "actual_24_25",
                    "budget_25_26",
                    "actual_25_26",
                    "budget_26_27",
                ]:
                    parsed[amount_field] = clean_ocr_amount(parsed[amount_field])
                row.update(parsed)
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

    return len(rows)
