from __future__ import annotations

import csv
import re
from pathlib import Path

SUSPICIOUS_CHARS_RE = re.compile(r"[§|{}\[\]<>]")
AMOUNT_RE = re.compile(r"^\(?-?\d[\d,]*\)?$")


def amount_looks_suspicious(value: str) -> bool:
    value = value.strip()
    if not value:
        return True
    if SUSPICIOUS_CHARS_RE.search(value):
        return True
    return AMOUNT_RE.fullmatch(value) is None


def account_looks_suspicious(account: str) -> bool:
    account = account.strip()
    if not account.isdigit():
        return True
    return len(account) not in {3, 4, 5}


def review_reasons(row: dict[str, str]) -> list[str]:
    reasons: list[str] = []

    account = row.get("account", "")
    label = row.get("label", "")
    raw_line = row.get("raw_line", "")

    if account_looks_suspicious(account):
        reasons.append("suspicious_account")

    if len(label.strip()) < 3:
        reasons.append("short_or_missing_label")

    if SUSPICIOUS_CHARS_RE.search(raw_line):
        reasons.append("suspicious_raw_character")

    for field in ["actual_24_25", "budget_25_26", "actual_25_26", "budget_26_27"]:
        if amount_looks_suspicious(row.get(field, "")):
            reasons.append(f"suspicious_{field}")

    if not row.get("fund_number"):
        reasons.append("missing_fund_number")

    if not row.get("section_hint"):
        reasons.append("missing_section_hint")

    if row.get("parse_status") != "parsed":
        reasons.append("not_parsed")

    return reasons


def build_ocr_review_queue(rows_path: Path, out_path: Path) -> int:
    rows = list(csv.DictReader(rows_path.open(encoding="utf-8")))
    if not rows:
        raise ValueError(f"no rows found in {rows_path}")

    fieldnames = ["review_reasons", *rows[0].keys()]
    review_rows = []

    for row in rows:
        reasons = review_reasons(row)
        if not reasons:
            continue

        review_row = dict(row)
        review_row["review_reasons"] = ";".join(reasons)
        review_rows.append(review_row)

    out_path.parent.mkdir(parents=True, exist_ok=True)

    with out_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(review_rows)

    return len(review_rows)
