from __future__ import annotations

import csv
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from budget_audit.reconcile import budget_side_from_section, material_delta, parse_amount

# Historical column pairs in chronological order. The final actual_25_26 ->
# budget_26_27 pair is deliberately not repeated here -- it is HEADLINE_TRANSITION
# below, so it is computed once, not once per label.
DELTA_TRANSITIONS: list[tuple[str, str, str]] = [
    ("actual_24_25", "budget_25_26", "actual_24_25_to_budget_25_26"),
    ("budget_25_26", "actual_25_26", "budget_25_26_to_actual_25_26"),
]
# The headline transition: most recent known actual vs. the budget being asked
# for next year. This is the only transition surfaced in findings.py.
HEADLINE_TRANSITION: tuple[str, str, str] = ("actual_25_26", "budget_26_27", "headline_actual_25_26_to_budget_26_27")


@dataclass(frozen=True)
class MaterialityThreshold:
    min_absolute: Decimal = Decimal("5000")
    min_percent: Decimal = Decimal("15")
    # Both thresholds by default: an "either" rule floods small-dollar lines
    # with noisy percent swings (e.g. $80 -> $100 is a 25% change but not a
    # meaningful public-transparency signal). A brand-new/zero-old-value line
    # is still caught on absolute dollars alone via the percent-is-None
    # fallback in is_material(), regardless of this setting.
    require_both: bool = True


@dataclass
class _FundDeltaAgg:
    material_count: int = 0
    total_absolute_delta: Decimal = Decimal("0")


def _to_decimal(raw: str) -> Decimal | None:
    amount = parse_amount(raw)
    return None if amount is None else Decimal(amount)


def is_material(
    absolute: Decimal | None,
    percent: Decimal | None,
    threshold: MaterialityThreshold,
) -> bool:
    """Decide materiality from an absolute/percent delta pair.

    A None percent (old value was zero, or unparseable) is treated as
    "cannot evaluate percent" rather than "not material" -- a brand-new
    $50,000 allocation should not be silently excluded just because the
    percent change from zero is undefined.
    """
    if absolute is None:
        return False
    abs_hit = abs(absolute) >= threshold.min_absolute
    if percent is None:
        return abs_hit
    pct_hit = abs(percent) >= threshold.min_percent
    if threshold.require_both:
        return abs_hit and pct_hit
    return abs_hit or pct_hit


def line_status(old_raw: str, new_raw: str) -> str:
    """Classify a line item transition as new / eliminated / present / blank_both."""
    old_blank = old_raw.strip() == ""
    new_blank = new_raw.strip() == ""
    if old_blank and new_blank:
        return "blank_both"
    if old_blank and not new_blank:
        return "new"
    if not old_blank and new_blank:
        return "eliminated"
    return "present"


def analyze_deltas(
    rows_path: Path,
    out_dir: Path,
    threshold: MaterialityThreshold = MaterialityThreshold(),
) -> dict[str, int]:
    """Compute per-line-item deltas across consecutive amount columns and a
    headline actual_25_26 -> budget_26_27 delta, for row_type == 'line_item' rows.

    Writes line_item_deltas.csv (one row per source row x transition) and
    delta_summary_by_fund.csv (material counts + total absolute delta per
    fund per transition, keyed on the headline transition).
    """
    rows = list(csv.DictReader(rows_path.open(encoding="utf-8")))
    if not rows:
        raise ValueError(f"no rows found in {rows_path}")

    out_dir.mkdir(parents=True, exist_ok=True)

    delta_rows: list[dict[str, str]] = []
    fund_summary: dict[tuple[str, str, str, str], _FundDeltaAgg] = {}

    line_items = [row for row in rows if row.get("row_type") == "line_item"]
    transitions = [*DELTA_TRANSITIONS, HEADLINE_TRANSITION]

    for row in line_items:
        fund_number = row.get("fund_number", "")
        fund_name = row.get("fund_name", "")
        budget_side = budget_side_from_section(row.get("section_hint", ""))

        for old_field, new_field, transition_label in transitions:
            old_raw = row.get(old_field, "")
            new_raw = row.get(new_field, "")
            status = line_status(old_raw, new_raw)

            old_val = _to_decimal(old_raw)
            new_val = _to_decimal(new_raw)
            absolute, percent = material_delta(old_val, new_val)
            material = is_material(absolute, percent, threshold)

            delta_rows.append(
                {
                    "document_id": row.get("document_id", ""),
                    "page_number": row.get("page_number", ""),
                    "fund_number": fund_number,
                    "fund_name": fund_name,
                    "budget_side": budget_side,
                    "division": row.get("division", ""),
                    "department": row.get("department", ""),
                    "account": row.get("account", ""),
                    "label": row.get("label", ""),
                    "transition": transition_label,
                    "old_field": old_field,
                    "new_field": new_field,
                    "old_value": "" if old_val is None else str(old_val),
                    "new_value": "" if new_val is None else str(new_val),
                    "absolute_delta": "" if absolute is None else str(absolute),
                    # Rounded for readability; materiality was already decided
                    # above using the unrounded percent value.
                    "percent_delta": "" if percent is None else str(percent.quantize(Decimal("0.01"))),
                    "status": status,
                    "material": "true" if material else "false",
                    "correction_action": row.get("correction_action", ""),
                }
            )

            if transition_label == HEADLINE_TRANSITION[2]:
                key = (fund_number, fund_name, budget_side, transition_label)
                agg = fund_summary.setdefault(key, _FundDeltaAgg())
                if material:
                    agg.material_count += 1
                if absolute is not None:
                    agg.total_absolute_delta += absolute

    delta_fieldnames = list(delta_rows[0].keys()) if delta_rows else []
    with (out_dir / "line_item_deltas.csv").open("w", newline="", encoding="utf-8") as handle:
        delta_writer = csv.DictWriter(handle, fieldnames=delta_fieldnames)
        delta_writer.writeheader()
        delta_writer.writerows(delta_rows)

    with (out_dir / "delta_summary_by_fund.csv").open("w", newline="", encoding="utf-8") as handle:
        summary_writer = csv.writer(handle)
        summary_writer.writerow(
            ["fund_number", "fund_name", "budget_side", "transition", "material_count", "total_absolute_delta"]
        )
        for (fund_number, fund_name, budget_side, transition), agg in sorted(fund_summary.items()):
            summary_writer.writerow(
                [fund_number, fund_name, budget_side, transition, agg.material_count, agg.total_absolute_delta]
            )

    # Stats are scoped to the headline transition, matching what findings.py
    # actually surfaces -- a historical transition being material/new/eliminated
    # is detail visible in line_item_deltas.csv, not a top-level count.
    headline_rows = [row for row in delta_rows if row["transition"] == HEADLINE_TRANSITION[2]]
    material_count = sum(1 for row in headline_rows if row["material"] == "true")
    new_count = sum(1 for row in headline_rows if row["status"] == "new")
    eliminated_count = sum(1 for row in headline_rows if row["status"] == "eliminated")

    return {
        "line_items": len(line_items),
        "delta_rows": len(delta_rows),
        "material_rows": material_count,
        "new_line_rows": new_count,
        "eliminated_line_rows": eliminated_count,
    }
