from __future__ import annotations

import csv
import re
from collections import Counter
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path

from budget_audit.classify import categorize_line_item
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
    "cluster_type",
    "narrative",
]

# A cluster's cluster_type is derived from the majority category among its
# member line items (via classify.categorize_line_item), not from a
# hardcoded list of prefixes -- this is what lets "JAIL"/"USDA"/"HVAC"/"CRT"
# debt clusters, "OPID"-style recipient-allocation clusters, and grant+capital
# pairings (e.g. Fund 172's Connected Communities Facilities grant paired
# with Building Construction) all fall out of the same general-purpose
# fund+prefix clustering already in place, instead of needing bespoke
# per-pattern detectors.
DEBT_LIKE_CATEGORIES = {"debt_service"}
ALLOCATION_LIKE_CATEGORIES = {"allocation_or_recipient_payment"}
PERSONNEL_LIKE_CATEGORIES = {"personnel", "benefits_or_payroll_burden"}
CAPITAL_LIKE_CATEGORIES = {"capital_project"}
GRANT_LIKE_CATEGORIES = {"grant_or_intergovernmental_revenue"}

MAJORITY_CLUSTER_TYPE = {
    frozenset(DEBT_LIKE_CATEGORIES): "debt_service",
    frozenset(ALLOCATION_LIKE_CATEGORIES): "allocation_program",
    frozenset(PERSONNEL_LIKE_CATEGORIES): "personnel_or_benefits",
}


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
    category_counts: Counter[str] = field(default_factory=Counter)
    sample_revenue_label: str = ""
    sample_expenditure_label: str = ""


def _cluster_type(agg: _ClusterAgg, is_paired: bool) -> str:
    """Derive a cluster's type from its member rows' categories.

    Grant-revenue pairing is checked before the majority-category fallback,
    not after: a school-program cluster like "ABE"/"SUM"/"ISM"/"PDG"/"TRN"
    typically has one grant-revenue line paired with several personnel/
    benefits expenditure lines, so a plain majority vote would call it
    'personnel_or_benefits' and hide the fact that it's grant-funded. Real
    validated examples: Fund 172's Connected Communities Facilities grant
    paired with Building Construction (-> grant_funded_capital_project) and
    Fund 101's ISIP emergency-management grant paired with equipment
    (-> grant_funded_capital_project); Fund 141's ABE/SUM/ISM/PDG/TRN school
    program clusters, paired but personnel-dominated (-> grant_funded_program).
    """
    if not agg.category_counts:
        return "general"

    categories_present = set(agg.category_counts)
    top_category, _count = agg.category_counts.most_common(1)[0]

    # Recipient-allocation as the majority category is checked before the
    # grant-pairing check below: OPID (opioid settlement revenue funding a
    # list of city/nonprofit recipients) is a paired cluster with a
    # grant-classified revenue line, but "who is money going to and why" is
    # the more important question here than "is this grant-funded" -- a
    # majority of named-recipient expenditure rows should win.
    if top_category in ALLOCATION_LIKE_CATEGORIES:
        return "allocation_program"

    if is_paired and GRANT_LIKE_CATEGORIES & categories_present:
        if CAPITAL_LIKE_CATEGORIES & categories_present:
            return "grant_funded_capital_project"
        return "grant_funded_program"

    for categories, cluster_type in MAJORITY_CLUSTER_TYPE.items():
        if top_category in categories:
            return cluster_type

    return "general"


def _narrative_for_cluster(agg: _ClusterAgg, cluster_type: str, is_paired: bool) -> str:
    fund_label = f"Fund {agg.fund_number} {agg.fund_name}".strip()
    samples = "; ".join(agg.sample_labels[:3]) if agg.sample_labels else "(no sample labels)"

    if cluster_type == "grant_funded_capital_project":
        revenue_label = agg.sample_revenue_label or "grant revenue"
        expenditure_label = agg.sample_expenditure_label or "capital expense"
        return (
            f"{fund_label} cluster '{agg.prefix}' appears to be a paired grant/construction project: "
            f"{revenue_label} revenue ({agg.revenue_total}) moves alongside {expenditure_label} expense "
            f"({agg.expenditure_total}). This should be reviewed as a project cluster rather than as "
            f"isolated line items. The first question is to request the grant award, project scope, "
            f"approved budget amendment, contracts, and commission minutes."
        )
    if cluster_type == "grant_funded_program":
        revenue_label = agg.sample_revenue_label or "grant revenue"
        return (
            f"{fund_label} cluster '{agg.prefix}' pairs {revenue_label} revenue ({agg.revenue_total}) "
            f"with program expenditure ({agg.expenditure_total}) across {agg.line_item_count} line "
            f"item(s) ({samples}), largely personnel/benefits costs. This looks like a grant- or "
            f"program-funded activity rather than an isolated line item. The first question is to "
            f"request the grant award letter, approved spending plan, and whether positions/activity "
            f"are grant-funded on a continuing basis."
        )
    if cluster_type == "debt_service":
        return (
            f"{fund_label} cluster '{agg.prefix}' represents a debt-service obligation (principal and/or "
            f"interest on notes or loans), totaling {agg.expenditure_total} across {agg.line_item_count} "
            f"line item(s) ({samples}). The first question is to request the debt schedule, note/loan "
            f"documents, repayment schedule, purpose of borrowing, and commission approval minutes."
        )
    if cluster_type == "allocation_program":
        return (
            f"{fund_label} cluster '{agg.prefix}' allocates {agg.expenditure_total} to named external "
            f"recipients ({samples}). The first question is what program authorizes these allocations, "
            f"who selected the recipients, and what criteria or scoring process was used."
        )
    if cluster_type == "personnel_or_benefits":
        return (
            f"{fund_label} cluster '{agg.prefix}' is a personnel/benefits grouping totaling "
            f"{agg.expenditure_total} across {agg.line_item_count} line item(s) ({samples}). The first "
            f"question is whether this reflects a headcount, rate, or classification change."
        )
    if is_paired:
        return (
            f"{fund_label} cluster '{agg.prefix}' has both revenue ({agg.revenue_total}) and expenditure "
            f"({agg.expenditure_total}) activity, the signature of a program pass-through -- worth "
            f"reviewing as a group rather than as isolated line items ({samples})."
        )
    side = "revenue" if agg.revenue_total != 0 else "expenditure"
    return (
        f"{fund_label} cluster '{agg.prefix}' appears entirely on the {side} side, totaling "
        f"{agg.revenue_total if side == 'revenue' else agg.expenditure_total} across "
        f"{agg.line_item_count} line item(s) ({samples})."
    )


def build_clusters(rows_path: Path, out_path: Path) -> dict[str, int]:
    """Group line_item rows by (fund_number, label prefix), aggregating
    revenue vs. expenditure totals via budget_side_from_section, and flag a
    cluster as 'paired' when it has nonzero totals on both sides -- the
    signature of a revenue/expense program pass-through (e.g. a grant
    revenue line paired with its recipient expenditure allocations).

    Also tags each cluster with a cluster_type (debt_service,
    grant_funded_capital_project, allocation_program, personnel_or_benefits,
    general) derived from the majority classify.categorize_line_item()
    category among its member rows, and a one-paragraph plain-English
    narrative -- see docs/report-design.md for why this stays a derived
    annotation on the existing dynamic clustering rather than a bespoke
    detector per pattern.

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

        section_hint = row.get("section_hint", "")
        budget_side = budget_side_from_section(section_hint)
        amount = parse_amount(row.get("budget_26_27", ""))
        if amount is not None:
            if budget_side == "revenue":
                agg.revenue_total += amount
                if not agg.sample_revenue_label:
                    agg.sample_revenue_label = label
            else:
                agg.expenditure_total += amount
                if not agg.sample_expenditure_label:
                    agg.sample_expenditure_label = label

        category = categorize_line_item(row.get("account", ""), label, budget_side)
        agg.category_counts[category] += 1

        agg.line_item_count += 1
        if label and label not in agg.sample_labels and len(agg.sample_labels) < 3:
            agg.sample_labels.append(label)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CLUSTER_FIELDNAMES)
        writer.writeheader()
        for (fund_number, prefix), agg in sorted(clusters.items()):
            is_paired = agg.revenue_total != 0 and agg.expenditure_total != 0
            cluster_type = _cluster_type(agg, is_paired)
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
                    "cluster_type": cluster_type,
                    "narrative": _narrative_for_cluster(agg, cluster_type, is_paired),
                }
            )

    paired_count = sum(1 for agg in clusters.values() if agg.revenue_total != 0 and agg.expenditure_total != 0)

    return {
        "clusters": len(clusters),
        "paired_clusters": paired_count,
        "unclustered_line_items": unclustered,
    }


__all__ = [
    "CLUSTER_FIELDNAMES",
    "build_clusters",
    "cluster_id_for",
    "extract_label_prefix",
]
