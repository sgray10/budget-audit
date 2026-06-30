from __future__ import annotations

import csv
import re
from pathlib import Path


TOTAL_RE = re.compile(
    r"\btotal\b|subtotal|grand total",
    re.IGNORECASE,
)

TRANSFER_RE = re.compile(
    r"transfers?|operating transfers?|from other funds|to other funds",
    re.IGNORECASE,
)

FUND_BALANCE_RE = re.compile(
    r"fund balance|assigned fund balance|unassigned fund balance|restricted fund balance",
    re.IGNORECASE,
)

COMPENSATION_RE = re.compile(
    r"salary|salaries|wage|wages|overtime|social security|retirement|medical insurance|medicare|payroll",
    re.IGNORECASE,
)


def classify_row(label: str, account: str) -> str:
    label = label.strip()

    if FUND_BALANCE_RE.search(label):
        return "fund_balance"
    if TRANSFER_RE.search(label):
        return "transfer"
    if TOTAL_RE.search(label):
        return "total"
    if account:
        return "line_item"
    return "unknown"


def classify_category(label: str) -> str:
    if COMPENSATION_RE.search(label):
        return "compensation"
    if TRANSFER_RE.search(label):
        return "transfer"
    if FUND_BALANCE_RE.search(label):
        return "fund_balance"
    return "operating"


def classify_ocr_rows(
    rows_path: Path,
    out_path: Path,
) -> int:
    rows = list(csv.DictReader(rows_path.open(encoding="utf-8")))
    if not rows:
        raise ValueError(f"no rows found in {rows_path}")

    fieldnames = list(rows[0].keys())
    for field in ["row_type", "category"]:
        if field not in fieldnames:
            fieldnames.insert(4, field)

    classified = []

    for row in rows:
        label = row.get("label", "")
        account = row.get("account", "")

        new_row = dict(row)
        new_row["row_type"] = classify_row(label, account)
        new_row["category"] = classify_category(label)
        classified.append(new_row)

    out_path.parent.mkdir(parents=True, exist_ok=True)

    with out_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(classified)

    return len(classified)
