from __future__ import annotations

import csv
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from budget_audit.reconcile import parse_amount

MANUAL_CORRECTION_FIELDNAMES = [
    "document_id",
    "page_number",
    "fund_number",
    "fund_name",
    "account",
    "label",
    "correction_action",
    "correction_reason",
    "budget_26_27",
]

# A correction is "high-impact by dollar amount" if the row it produced
# carries at least this much in the headline column -- distinct from a
# reconciliation-only $1 balancing correction, which is a real category
# (see docs/corrections.md) but not one that changes a reader's picture of
# the budget.
HIGH_IMPACT_CORRECTION_FLOOR = 5000


@dataclass(frozen=True)
class ManualCorrectionSummary:
    total: int
    by_fund: dict[str, int]
    by_action: dict[str, int]
    high_impact: list[dict[str, str]]


def manual_correction_rows(rows_path: Path) -> list[dict[str, str]]:
    """Full list of consolidated rows that depend on a manual correction,
    for Appendix C. One row per corrected line item, not per correction
    file -- a row's correction_action/correction_reason columns are set by
    corrections.apply_row_corrections at extraction time.
    """
    rows = list(csv.DictReader(rows_path.open(encoding="utf-8")))
    corrected = [row for row in rows if row.get("correction_action", "")]
    return [
        {
            "document_id": row.get("document_id", ""),
            "page_number": row.get("page_number", ""),
            "fund_number": row.get("fund_number", ""),
            "fund_name": row.get("fund_name", ""),
            "account": row.get("account", ""),
            "label": row.get("label", ""),
            "correction_action": row.get("correction_action", ""),
            "correction_reason": row.get("correction_reason", ""),
            "budget_26_27": row.get("budget_26_27", ""),
        }
        for row in corrected
    ]


def summarize_manual_corrections(rows_path: Path) -> ManualCorrectionSummary:
    corrected = manual_correction_rows(rows_path)

    by_fund: Counter[str] = Counter(row["fund_number"] for row in corrected)
    by_action: Counter[str] = Counter(row["correction_action"] for row in corrected)

    high_impact = []
    for row in corrected:
        amount = parse_amount(row.get("budget_26_27", ""))
        if amount is not None and abs(amount) >= HIGH_IMPACT_CORRECTION_FLOOR:
            high_impact.append(row)
    high_impact.sort(key=lambda row: abs(parse_amount(row["budget_26_27"]) or 0), reverse=True)

    return ManualCorrectionSummary(
        total=len(corrected),
        by_fund=dict(sorted(by_fund.items())),
        by_action=dict(sorted(by_action.items())),
        high_impact=high_impact,
    )


def write_manual_corrections(rows_path: Path, out_path: Path) -> int:
    corrected = manual_correction_rows(rows_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=MANUAL_CORRECTION_FIELDNAMES)
        writer.writeheader()
        writer.writerows(corrected)
    return len(corrected)


__all__ = [
    "ManualCorrectionSummary",
    "manual_correction_rows",
    "summarize_manual_corrections",
    "write_manual_corrections",
]
