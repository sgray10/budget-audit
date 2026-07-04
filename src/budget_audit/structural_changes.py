from __future__ import annotations

import csv
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from budget_audit.classify import categorize_line_item

HEADLINE_TRANSITION_LABEL = "headline_actual_25_26_to_budget_26_27"

# A fund is only considered "materially active" on a side (revenue or
# expenditure) if its old-side total clears this floor -- avoids flagging a
# fund that was already near-zero as a "structural change" when it drifts a
# few hundred dollars further toward zero.
WHOLE_FUND_ACTIVE_FLOOR = Decimal("10000")
WHOLE_FUND_ZERO_CEILING = Decimal("1000")

# For fund-level grant/capital pairing (distinct from clusters.py's
# shared-label-prefix clustering, which can't catch a pair like Fund 172's
# "Other State Grants - Connected Communities Facilities" revenue moving
# with "Building Construction" expense -- neither label has a common
# prefix). A pairing candidate must itself be a large, real dollar move; the
# ratio check keeps a small grant next to an unrelated large capital project
# from being flagged as if they were connected.
GRANT_CAPITAL_PAIR_FLOOR = Decimal("25000")
GRANT_CAPITAL_PAIR_MIN_RATIO = Decimal("0.2")


@dataclass(frozen=True)
class WholeFundChange:
    fund_number: str
    fund_name: str
    direction: str  # "zeroed_out" or "newly_active"
    revenue_old: Decimal
    revenue_new: Decimal
    expenditure_old: Decimal
    expenditure_new: Decimal
    sample_labels: list[str]


@dataclass(frozen=True)
class GrantFundedCapitalPair:
    fund_number: str
    fund_name: str
    revenue_label: str
    revenue_delta: Decimal
    expenditure_label: str
    expenditure_delta: Decimal


def _to_decimal(value: str) -> Decimal | None:
    stripped = value.strip()
    return Decimal(stripped) if stripped else None


def _headline_rows(delta_rows_path: Path) -> list[dict[str, str]]:
    rows = list(csv.DictReader(delta_rows_path.open(encoding="utf-8")))
    if not rows:
        raise ValueError(f"no rows found in {delta_rows_path}")
    return [row for row in rows if row.get("transition") == HEADLINE_TRANSITION_LABEL]


def detect_whole_fund_changes(delta_rows_path: Path) -> list[WholeFundChange]:
    """Flag funds where revenue and expenditure both collapse from
    materially active to ~zero (or the reverse) on the headline transition --
    the pattern a fund being wound down, newly stood up, or reclassified
    produces. Validated against Fund 202 Nursing Home, whose Patient Charges
    revenue and Remittance of Revenue Collected expenditure both go to zero.
    """
    rows = _headline_rows(delta_rows_path)

    by_fund: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        by_fund.setdefault(row["fund_number"], []).append(row)

    changes: list[WholeFundChange] = []
    for fund_number, fund_rows in sorted(by_fund.items()):
        fund_name = fund_rows[0].get("fund_name", "")
        revenue_old = Decimal("0")
        revenue_new = Decimal("0")
        expenditure_old = Decimal("0")
        expenditure_new = Decimal("0")
        sample_labels: list[str] = []

        for row in fund_rows:
            old_val = _to_decimal(row.get("old_value", "")) or Decimal("0")
            new_val = _to_decimal(row.get("new_value", "")) or Decimal("0")
            if row.get("budget_side") == "revenue":
                revenue_old += old_val
                revenue_new += new_val
            elif row.get("budget_side") == "expenditure":
                expenditure_old += old_val
                expenditure_new += new_val
            if old_val != 0 and new_val == 0 and len(sample_labels) < 3:
                sample_labels.append(row.get("label", ""))

        zeroed_out = (
            revenue_old >= WHOLE_FUND_ACTIVE_FLOOR
            and expenditure_old >= WHOLE_FUND_ACTIVE_FLOOR
            and abs(revenue_new) <= WHOLE_FUND_ZERO_CEILING
            and abs(expenditure_new) <= WHOLE_FUND_ZERO_CEILING
        )
        newly_active = (
            revenue_new >= WHOLE_FUND_ACTIVE_FLOOR
            and expenditure_new >= WHOLE_FUND_ACTIVE_FLOOR
            and abs(revenue_old) <= WHOLE_FUND_ZERO_CEILING
            and abs(expenditure_old) <= WHOLE_FUND_ZERO_CEILING
        )

        if zeroed_out or newly_active:
            changes.append(
                WholeFundChange(
                    fund_number=fund_number,
                    fund_name=fund_name,
                    direction="zeroed_out" if zeroed_out else "newly_active",
                    revenue_old=revenue_old,
                    revenue_new=revenue_new,
                    expenditure_old=expenditure_old,
                    expenditure_new=expenditure_new,
                    sample_labels=sample_labels,
                )
            )

    return changes


def detect_grant_funded_capital_pairs(delta_rows_path: Path) -> list[GrantFundedCapitalPair]:
    """Flag funds with a material grant/intergovernmental-revenue increase
    paired with a material capital-expense increase of comparable
    magnitude, even when the two labels share no common prefix (so
    clusters.py's shared-prefix clustering can't group them). Validated
    against Fund 172: "Other State Grants - Connected Communities
    Facilities" revenue (+$1,443,340) paired with "Building Construction"
    expense (+$1,603,710) -- comparable magnitude, no shared prefix.
    """
    rows = _headline_rows(delta_rows_path)

    by_fund: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        by_fund.setdefault(row["fund_number"], []).append(row)

    pairs: list[GrantFundedCapitalPair] = []
    for fund_number, fund_rows in sorted(by_fund.items()):
        fund_name = fund_rows[0].get("fund_name", "")
        best_revenue: tuple[str, Decimal] | None = None
        best_expenditure: tuple[str, Decimal] | None = None

        for row in fund_rows:
            budget_side = row.get("budget_side", "")
            category = categorize_line_item(row.get("account", ""), row.get("label", ""), budget_side)
            delta = _to_decimal(row.get("absolute_delta", ""))
            if delta is None or delta <= 0:
                continue

            if category == "grant_or_intergovernmental_revenue" and delta >= GRANT_CAPITAL_PAIR_FLOOR:
                if best_revenue is None or delta > best_revenue[1]:
                    best_revenue = (row.get("label", ""), delta)
            if category == "capital_project" and delta >= GRANT_CAPITAL_PAIR_FLOOR:
                if best_expenditure is None or delta > best_expenditure[1]:
                    best_expenditure = (row.get("label", ""), delta)

        if best_revenue is None or best_expenditure is None:
            continue

        smaller, larger = sorted([best_revenue[1], best_expenditure[1]])
        if smaller / larger < GRANT_CAPITAL_PAIR_MIN_RATIO:
            continue

        pairs.append(
            GrantFundedCapitalPair(
                fund_number=fund_number,
                fund_name=fund_name,
                revenue_label=best_revenue[0],
                revenue_delta=best_revenue[1],
                expenditure_label=best_expenditure[0],
                expenditure_delta=best_expenditure[1],
            )
        )

    return pairs


__all__ = [
    "GrantFundedCapitalPair",
    "WholeFundChange",
    "detect_grant_funded_capital_pairs",
    "detect_whole_fund_changes",
]
