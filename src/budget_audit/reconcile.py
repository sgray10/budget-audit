from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path


@dataclass(frozen=True)
class ReconciliationResult:
    label: str
    expected: Decimal
    actual: Decimal
    difference: Decimal
    passed: bool


def reconcile_total(label: str, expected: Decimal, values: list[Decimal], tolerance: Decimal = Decimal("0.00")) -> ReconciliationResult:
    """Compare a stated total to the sum of extracted values."""
    actual = sum(values, Decimal("0"))
    difference = actual - expected
    return ReconciliationResult(
        label=label,
        expected=expected,
        actual=actual,
        difference=difference,
        passed=abs(difference) <= tolerance,
    )


def material_delta(old: Decimal | None, new: Decimal | None) -> tuple[Decimal | None, Decimal | None]:
    """Return absolute and percent delta.

    Percent delta is returned as a percentage, e.g. 12.5 means +12.5%.
    """
    if old is None or new is None:
        return None, None
    absolute = new - old
    if old == 0:
        return absolute, None
    return absolute, (absolute / abs(old)) * Decimal("100")


def parse_amount(value: str) -> int | None:
    value = value.strip()
    if not value:
        return None

    negative = value.startswith("(") and value.endswith(")")
    cleaned = value.strip("()").replace(",", "").replace("$", "")

    if not re.fullmatch(r"-?\d+", cleaned):
        return None

    amount = int(cleaned)
    return -amount if negative else amount


def budget_side_from_section(section_hint: str) -> str:
    normalized = section_hint.lower()
    if "revenue" in normalized:
        return "revenue"
    if "summary" in normalized:
        return "summary"
    return "expenditure"


def reconcile_fund(
    rows_path: Path,
    out_path: Path,
    fund_number: str,
) -> dict[str, int | str]:
    rows = list(csv.DictReader(rows_path.open(encoding="utf-8")))
    if not rows:
        raise ValueError(f"no rows found in {rows_path}")

    revenue_line_items = 0
    expenditure_line_items = 0
    transfer_in = 0
    transfer_out = 0
    unparsed_amounts = 0

    for row in rows:
        if row.get("fund_number") != fund_number:
            continue

        amount = parse_amount(row.get("budget_26_27", ""))
        if amount is None:
            unparsed_amounts += 1
            continue

        row_type = row.get("row_type", "")
        label = row.get("label", "")
        budget_side = budget_side_from_section(row.get("section_hint", ""))

        if row_type == "line_item":
            if budget_side == "revenue":
                revenue_line_items += amount
            elif budget_side == "expenditure":
                expenditure_line_items += amount
        elif row_type == "transfer":
            if " in" in label.lower():
                transfer_in += amount
            else:
                transfer_out += amount

    revenue_with_transfers = revenue_line_items + transfer_in
    expenditure_with_transfers = expenditure_line_items + transfer_out
    net_line_items = revenue_line_items - expenditure_line_items
    net_with_transfers = revenue_with_transfers - expenditure_with_transfers

    out_path.parent.mkdir(parents=True, exist_ok=True)

    rows_out: list[tuple[str, int | str]] = [
        ("fund_number", fund_number),
        ("revenue_line_items", revenue_line_items),
        ("transfer_in", transfer_in),
        ("revenue_with_transfers", revenue_with_transfers),
        ("expenditure_line_items", expenditure_line_items),
        ("transfer_out", transfer_out),
        ("expenditure_with_transfers", expenditure_with_transfers),
        ("net_line_items", net_line_items),
        ("net_with_transfers", net_with_transfers),
        ("unparsed_amounts", unparsed_amounts),
    ]

    with out_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["metric", "value"])
        writer.writerows(rows_out)

    return dict(rows_out)
