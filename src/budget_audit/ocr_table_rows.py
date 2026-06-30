from __future__ import annotations

import csv
import re
from pathlib import Path

ACCOUNT_ROW_RE = re.compile(
    r"^\s*(?P<account>\d{3,5})\s+(?P<label>.*?)\s+"
    r"(?P<actual_24_25>[\d,§,().-]+(?:\s+[\d,§,().-]+)*)\s+"
    r"(?P<budget_25_26>[\d,§,().-]+(?:\s+[\d,§,().-]+)*)\s+"
    r"(?P<actual_25_26>[\d,§,().-]+(?:\s+[\d,§,().-]+)*)\s+"
    r"(?P<budget_26_27>[\d,§,().-]+(?:\s+[\d,§,().-]+)*)\s*$"
)

HEADER_HINT_RE = re.compile(
    r"fund number|fund:|revenue|expenditure|actual|budget|department|division",
    re.IGNORECASE,
)


def clean_ocr_amount(value: str) -> str:
    """Clean common OCR artifacts in amount fields."""
    cleaned = value.replace("§", "5")
    cleaned = re.sub(r"(?<=\d)\.(?=\d{3}\b)", ",", cleaned)
    cleaned = re.sub(r"\s+", "", cleaned)
    return cleaned


def classify_raw_line(line: str) -> str:
    stripped = line.strip()
    if not stripped:
        return "blank"
    if ACCOUNT_ROW_RE.match(stripped):
        return "account_row"
    if HEADER_HINT_RE.search(stripped):
        return "header_or_context"
    if re.fullmatch(r"\d{3,5}", stripped):
        return "account_group"
    return "unclassified"


def extract_ocr_table_rows(
    ocr_dir: Path,
    out_path: Path,
    document_id: str,
) -> int:
    """Extract likely OCR budget table rows into a CSV review file."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, str]] = []

    for text_path in sorted(ocr_dir.glob("page-*.txt")):
        page_number = int(text_path.stem.removeprefix("page-"))
        lines = text_path.read_text(encoding="utf-8").splitlines()

        current_context = ""
        for line_number, line in enumerate(lines, start=1):
            line_type = classify_raw_line(line)

            if line_type in {"header_or_context", "account_group"}:
                current_context = line.strip()

            if line_type != "account_row":
                continue

            match = ACCOUNT_ROW_RE.match(line)
            if match is None:
                continue

            parsed = match.groupdict()
            for amount_field in [
                "actual_24_25",
                "budget_25_26",
                "actual_25_26",
                "budget_26_27",
            ]:
                parsed[amount_field] = clean_ocr_amount(parsed[amount_field])

            rows.append(
                {
                    "document_id": document_id,
                    "page_number": str(page_number),
                    "line_number": str(line_number),
                    "context_hint": current_context,
                    "account": parsed["account"],
                    "label": parsed["label"],
                    "actual_24_25": parsed["actual_24_25"],
                    "budget_25_26": parsed["budget_25_26"],
                    "actual_25_26": parsed["actual_25_26"],
                    "budget_26_27": parsed["budget_26_27"],
                    "parse_status": "parsed",
                    "raw_line": line,
                }
            )

    with out_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "document_id",
                "page_number",
                "line_number",
                "context_hint",
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
