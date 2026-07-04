from __future__ import annotations

import csv
import re
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path

from budget_audit.reconcile import budget_side_from_section, parse_amount

# Matches a short leading department/program code before a capitalized word,
# e.g. "OPID Opioid Settlement Funds", "BONUS Social Security", "+ISM State
# Retirement" (the "+"/"="/"~" variants are real OCR artifacts on department
# codes, confirmed in compensation.py's PREFIXED_AGGREGATE_RE). Detected
# dynamically rather than from a fixed list -- real data shows dozens of
# distinct prefixes (BONUS, ISM, OPID, PDG, SPED, TRN, THSO, DGA, SUM, ELTG,
# ABE, CSH, ITG, FRM, and more), with no way to enumerate them all up front.
PREFIX_RE = re.compile(r"^([A-Z0-9=+~]{2,8})\s+[A-Z][a-z]")

CLUSTER_FIELDNAMES = [
    "cluster_id",
    "fund_number",
    "fund_name",
    "prefix",
    "revenue_total",
    "expenditure_total",
    "is_paired",
    "line_item_count",
    "sample_labels",
]


def extract_label_prefix(label: str) -> str | None:
    """Extract a short leading program/department code from a label, if present.

    This is a coarse, low-confidence grouping signal, not a semantic
    classification -- two rows sharing a prefix are not guaranteed to be
    related, only likely to be worth reviewing together. See
    compensation.classify_compensation_label for the same posture applied
    to a different heuristic.
    """
    match = PREFIX_RE.match(label.strip())
    return match.group(1) if match else None


def cluster_id_for(fund_number: str, prefix: str) -> str:
    return f"{fund_number}-{prefix}"


@dataclass
class _ClusterAgg:
    fund_number: str
    fund_name: str
    prefix: str
    revenue_total: Decimal = Decimal("0")
    expenditure_total: Decimal = Decimal("0")
    line_item_count: int = 0
    sample_labels: list[str] = field(default_factory=list)


def build_clusters(rows_path: Path, out_path: Path) -> dict[str, int]:
    """Group line_item rows by (fund_number, label prefix), aggregating
    revenue vs. expenditure totals via budget_side_from_section, and flag a
    cluster as 'paired' when it has nonzero totals on both sides -- the
    signature of a revenue/expense program pass-through (e.g. a grant
    revenue line paired with its recipient expenditure allocations).

    Writes clusters.csv. Comparison is scoped to budget_26_27 only,
    consistent with the rest of this codebase's headline-column convention.
    """
    rows = list(csv.DictReader(rows_path.open(encoding="utf-8")))
    if not rows:
        raise ValueError(f"no rows found in {rows_path}")

    clusters: dict[tuple[str, str], _ClusterAgg] = {}
    unclustered = 0

    for row in rows:
        if row.get("row_type") != "line_item":
            continue

        label = row.get("label", "")
        prefix = extract_label_prefix(label)
        if prefix is None:
            unclustered += 1
            continue

        fund_number = row.get("fund_number", "")
        key = (fund_number, prefix)
        agg = clusters.setdefault(
            key,
            _ClusterAgg(fund_number=fund_number, fund_name=row.get("fund_name", ""), prefix=prefix),
        )

        amount = parse_amount(row.get("budget_26_27", ""))
        if amount is not None:
            budget_side = budget_side_from_section(row.get("section_hint", ""))
            if budget_side == "revenue":
                agg.revenue_total += amount
            else:
                agg.expenditure_total += amount

        agg.line_item_count += 1
        if label and label not in agg.sample_labels and len(agg.sample_labels) < 3:
            agg.sample_labels.append(label)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CLUSTER_FIELDNAMES)
        writer.writeheader()
        for (fund_number, prefix), agg in sorted(clusters.items()):
            is_paired = agg.revenue_total != 0 and agg.expenditure_total != 0
            writer.writerow(
                {
                    "cluster_id": cluster_id_for(fund_number, prefix),
                    "fund_number": fund_number,
                    "fund_name": agg.fund_name,
                    "prefix": prefix,
                    "revenue_total": str(agg.revenue_total),
                    "expenditure_total": str(agg.expenditure_total),
                    "is_paired": "true" if is_paired else "false",
                    "line_item_count": agg.line_item_count,
                    "sample_labels": "; ".join(agg.sample_labels),
                }
            )

    paired_count = sum(1 for agg in clusters.values() if agg.revenue_total != 0 and agg.expenditure_total != 0)

    return {
        "clusters": len(clusters),
        "paired_clusters": paired_count,
        "unclustered_line_items": unclustered,
    }
