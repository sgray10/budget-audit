from __future__ import annotations

import csv
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from budget_audit.reconcile import parse_amount

TOLERANCE = Decimal("0")


@dataclass
class SubtotalGroup:
    fund_number: str
    start_page: str
    start_line: str
    end_page: str
    end_line: str
    line_item_count: int = 0
    expected: Decimal = Decimal("0")
    unparsed_line_items: int = 0


def _sort_key(row: dict[str, str]) -> tuple[str, int, int]:
    try:
        page = int(row.get("page_number", "0") or "0")
    except ValueError:
        page = 0
    try:
        line = int(row.get("line_number", "0") or "0")
    except ValueError:
        line = 0
    return (row.get("fund_number", ""), page, line)


def _reset_group(fund_number: str, page: str, line: str) -> SubtotalGroup:
    return SubtotalGroup(
        fund_number=fund_number,
        start_page=page,
        start_line=line,
        end_page=page,
        end_line=line,
    )


def reconcile_subtotals(
    rows_path: Path,
    out_path: Path,
    tolerance: Decimal = TOLERANCE,
) -> dict[str, int]:
    """Walk corrected/classified rows in document order and compare each
    total/subtotal row's own budget_26_27 amount against the sum of the
    preceding contiguous run of line_item rows since the last total row
    (or start of fund).

    Grouping is positional/sequential, not semantic (it does not parse what
    a subtotal label logically belongs to) -- the same "coarse, documented
    heuristic for human review" posture as
    compensation.classify_compensation_label. Continuation pages are handled
    implicitly because grouping follows (page_number, line_number) document
    order, not per-page boundaries.

    Comparison is scoped to budget_26_27 only, consistent with
    reconcile.reconcile_fund and the headline-column convention used
    throughout this codebase.
    """
    rows = list(csv.DictReader(rows_path.open(encoding="utf-8")))
    if not rows:
        raise ValueError(f"no rows found in {rows_path}")

    ordered = sorted(rows, key=_sort_key)

    mismatches: list[dict[str, str]] = []
    stats = {
        "total_rows_seen": 0,
        "compared": 0,
        "matched": 0,
        "mismatched": 0,
        "skipped_zero_line_item_groups": 0,
        "unparsed_total_amounts": 0,
    }

    current_fund: str | None = None
    group: SubtotalGroup | None = None

    for row in ordered:
        fund_number = row.get("fund_number", "")
        page = row.get("page_number", "")
        line = row.get("line_number", "")
        row_type = row.get("row_type", "")

        if fund_number != current_fund:
            current_fund = fund_number
            group = _reset_group(fund_number, page, line)

        assert group is not None

        if row_type == "line_item":
            amount = parse_amount(row.get("budget_26_27", ""))
            group.line_item_count += 1
            group.end_page = page
            group.end_line = line
            if amount is None:
                group.unparsed_line_items += 1
            else:
                group.expected += amount
            continue

        if row_type != "total":
            continue

        stats["total_rows_seen"] += 1
        total_amount = parse_amount(row.get("budget_26_27", ""))

        if group.line_item_count == 0:
            # Roll-up/restated total immediately following another total
            # (e.g. "Total Expense" followed by "Total <Department>") -- not
            # an error, nothing to reconcile against.
            stats["skipped_zero_line_item_groups"] += 1
            group = _reset_group(fund_number, page, line)
            continue

        if total_amount is None:
            stats["unparsed_total_amounts"] += 1
            mismatches.append(
                {
                    "fund_number": fund_number,
                    "start_page": group.start_page,
                    "start_line": group.start_line,
                    "end_page": group.end_page,
                    "end_line": group.end_line,
                    "total_page": page,
                    "total_line": line,
                    "label": row.get("label", ""),
                    "total_raw_line": row.get("raw_line", ""),
                    "line_item_count": str(group.line_item_count),
                    "expected": str(group.expected),
                    "actual": "",
                    "difference": "",
                    "within_tolerance": "false",
                    "unparsed_line_items": str(group.unparsed_line_items),
                    "confidence": "low",
                    "note": "total_amount_unparsed",
                }
            )
            stats["mismatched"] += 1
            group = _reset_group(fund_number, page, line)
            continue

        stats["compared"] += 1
        difference = group.expected - total_amount
        within_tolerance = abs(difference) <= tolerance
        confidence = "low" if group.unparsed_line_items > 0 else "high"

        if within_tolerance:
            stats["matched"] += 1
        else:
            stats["mismatched"] += 1
            mismatches.append(
                {
                    "fund_number": fund_number,
                    "start_page": group.start_page,
                    "start_line": group.start_line,
                    "end_page": group.end_page,
                    "end_line": group.end_line,
                    "total_page": page,
                    "total_line": line,
                    "label": row.get("label", ""),
                    "total_raw_line": row.get("raw_line", ""),
                    "line_item_count": str(group.line_item_count),
                    "expected": str(group.expected),
                    "actual": str(total_amount),
                    "difference": str(difference),
                    "within_tolerance": "false",
                    "unparsed_line_items": str(group.unparsed_line_items),
                    "confidence": confidence,
                    "note": "",
                }
            )

        group = _reset_group(fund_number, page, line)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "fund_number",
        "start_page",
        "start_line",
        "end_page",
        "end_line",
        "total_page",
        "total_line",
        "label",
        "total_raw_line",
        "line_item_count",
        "expected",
        "actual",
        "difference",
        "within_tolerance",
        "unparsed_line_items",
        "confidence",
        "note",
    ]
    with out_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(mismatches)

    return stats
