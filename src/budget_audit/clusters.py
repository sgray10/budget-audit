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
    "capital_expenditure_total",
    "is_paired",
    "line_item_count",
    "sample_labels",
    "cluster_type",
    "narrative",
    "key_revenue_line",
    "key_expenditure_line",
]

# Capital dominance thresholds for typing a paired grant cluster, measured as
# capital-classified dollars / total expenditure dollars in the cluster.
# Calibrated against the real Weakley data before being chosen: 101-CRD and
# 101-ISIP are 100% capital (clearly projects), 141-ISM is 73% capital but
# with $112k of real personnel/benefits spending alongside it, 141-PDG is
# 59/41 -- both of those are "a program that includes equipment/building
# money", not "a construction project", so they should read as mixed rather
# than capital. A cluster must be nearly-all capital to be called a capital
# project, nearly-none to be called a plain program, and anything in between
# is explicitly mixed.
CAPITAL_DOMINANT_SHARE = Decimal("0.8")
CAPITAL_IMMATERIAL_SHARE = Decimal("0.2")

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

# Appended to the narrative of any cluster with activity on only one side --
# a one-sided cluster is not inherently anomalous, and the report should say
# why before a reader over-reads it.
ONE_SIDED_NOTE = (
    "This appears one-sided within the extracted packet pages. That may be normal if the "
    "offsetting entry is in another fund, fund balance, debt proceeds, transfers, or a "
    "non-extracted schedule; it should be reviewed with the full packet/source accounting context."
)


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
class _KeyLine:
    label: str = ""
    page: str = ""
    account: str = ""
    amount: Decimal = Decimal("0")

    def render(self) -> str:
        if not self.label:
            return ""
        return f"page={self.page} account={self.account} label={self.label} budget_26_27={self.amount}"


@dataclass
class _ClusterAgg:
    fund_number: str
    fund_name: str
    prefix: str
    revenue_total: Decimal = Decimal("0")
    expenditure_total: Decimal = Decimal("0")
    capital_expenditure_total: Decimal = Decimal("0")
    line_item_count: int = 0
    sample_labels: list[str] = field(default_factory=list)
    category_counts: Counter[str] = field(default_factory=Counter)
    key_revenue_line: _KeyLine = field(default_factory=_KeyLine)
    key_expenditure_line: _KeyLine = field(default_factory=_KeyLine)


def _capital_share(agg: _ClusterAgg) -> Decimal:
    if agg.expenditure_total == 0:
        return Decimal("0")
    return agg.capital_expenditure_total / agg.expenditure_total


def _cluster_type(agg: _ClusterAgg, is_paired: bool) -> str:
    """Derive a cluster's type from its member rows' categories and, for
    paired grant clusters, the capital share of expenditure dollars.

    Recipient-allocation as the majority category is checked before the
    grant-pairing check: OPID (opioid settlement revenue funding a list of
    city/nonprofit recipients) is a paired cluster with a grant-classified
    revenue line, but "who is money going to and why" is the more important
    question there than "is this grant-funded".

    Grant-revenue pairing is checked before the majority-category fallback:
    a school-program cluster like ABE/SUM/TRN typically has one grant-revenue
    line paired with several personnel/benefits expenditure lines, so a plain
    majority vote would call it personnel_or_benefits and hide that it's
    grant-funded. Within paired grant clusters, the capital-dollar share
    (not line count) picks between grant_funded_capital_project (capital
    dominates -- a construction/equipment project), grant_funded_program
    (capital immaterial -- a staffed program), and mixed_grant_program
    (both meaningful). See CAPITAL_DOMINANT_SHARE for the real clusters
    these thresholds were calibrated against.
    """
    if not agg.category_counts:
        return "general"

    categories_present = set(agg.category_counts)
    top_category, _count = agg.category_counts.most_common(1)[0]

    if top_category in ALLOCATION_LIKE_CATEGORIES:
        return "allocation_program"

    if is_paired and GRANT_LIKE_CATEGORIES & categories_present:
        share = _capital_share(agg)
        if share >= CAPITAL_DOMINANT_SHARE:
            return "grant_funded_capital_project"
        if share > CAPITAL_IMMATERIAL_SHARE:
            return "mixed_grant_program"
        return "grant_funded_program"

    for categories, cluster_type in MAJORITY_CLUSTER_TYPE.items():
        if top_category in categories:
            return cluster_type

    return "general"


def _narrative_for_cluster(agg: _ClusterAgg, cluster_type: str, is_paired: bool) -> str:
    fund_label = f"Fund {agg.fund_number} {agg.fund_name}".strip()
    samples = "; ".join(agg.sample_labels[:3]) if agg.sample_labels else "(no sample labels)"
    one_sided_suffix = "" if is_paired else f" {ONE_SIDED_NOTE}"

    if cluster_type == "grant_funded_capital_project":
        revenue_label = agg.key_revenue_line.label or "grant revenue"
        expenditure_label = agg.key_expenditure_line.label or "capital expense"
        return (
            f"{fund_label} cluster '{agg.prefix}' appears to be a paired grant/construction project: "
            f"{revenue_label} revenue ({agg.revenue_total}) moves alongside {expenditure_label} expense "
            f"({agg.expenditure_total}, of which {agg.capital_expenditure_total} is capital-classified). "
            f"This should be reviewed as a project cluster rather than as isolated line items. This may "
            f"simply reflect a grant-funded project or budget amendment, but the packet alone does not "
            f"provide the project scope, match requirements, vendors, or approval path. The first "
            f"question is to request the grant award, project scope, approved budget amendment, "
            f"contracts, and commission minutes." + one_sided_suffix
        )
    if cluster_type == "mixed_grant_program":
        revenue_label = agg.key_revenue_line.label or "grant revenue"
        return (
            f"{fund_label} cluster '{agg.prefix}' pairs {revenue_label} revenue ({agg.revenue_total}) "
            f"with a mix of program costs (personnel/benefits/supplies) and capital costs "
            f"({agg.capital_expenditure_total} of {agg.expenditure_total} expenditure is "
            f"capital-classified) across {agg.line_item_count} line item(s) ({samples}). This may "
            f"reflect normal restricted grant accounting covering both staffing and equipment/"
            f"facilities, but the packet alone does not show award terms or allowed uses. The first "
            f"question is to request the grant award letter, approved budget, allowed-use rules, and "
            f"spending plan." + one_sided_suffix
        )
    if cluster_type == "grant_funded_program":
        revenue_label = agg.key_revenue_line.label or "grant revenue"
        return (
            f"{fund_label} cluster '{agg.prefix}' pairs {revenue_label} revenue ({agg.revenue_total}) "
            f"with program expenditure ({agg.expenditure_total}) across {agg.line_item_count} line "
            f"item(s) ({samples}), largely personnel/benefits costs. This looks like a grant- or "
            f"program-funded activity rather than an isolated line item. This may reflect normal "
            f"restricted grant accounting, but the packet alone does not show award terms, allowed "
            f"uses, duration, or whether positions are continuing. The first question is to request "
            f"the grant award letter, approved spending plan, and whether positions/activity are "
            f"grant-funded on a continuing basis." + one_sided_suffix
        )
    if cluster_type == "debt_service":
        return (
            f"{fund_label} cluster '{agg.prefix}' represents a debt-service obligation (principal and/or "
            f"interest on notes or loans), totaling {agg.expenditure_total} across {agg.line_item_count} "
            f"line item(s) ({samples}). This may reflect ordinary debt issuance, refinancing, repayment "
            f"timing, or note retirement, but the packet alone does not provide the debt schedule or "
            f"approval context. The first question is to request the debt schedule, note/loan documents, "
            f"repayment schedule, purpose of borrowing, and commission approval minutes." + one_sided_suffix
        )
    if cluster_type == "allocation_program":
        return (
            f"{fund_label} cluster '{agg.prefix}' allocates {agg.expenditure_total} to named external "
            f"recipients ({samples}). This may reflect an authorized grant or settlement-funded "
            f"allocation process, but the packet alone does not show recipient selection criteria, "
            f"applications, award letters, or deliverables. The first question is what program "
            f"authorizes these allocations, who selected the recipients, and what criteria or scoring "
            f"process was used." + one_sided_suffix
        )
    if cluster_type == "personnel_or_benefits":
        return (
            f"{fund_label} cluster '{agg.prefix}' is a personnel/benefits grouping totaling "
            f"{agg.expenditure_total} across {agg.line_item_count} line item(s) ({samples}). The first "
            f"question is whether this reflects a headcount, rate, or classification change."
            + one_sided_suffix
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
        f"{agg.line_item_count} line item(s) ({samples}). {ONE_SIDED_NOTE}"
    )


def build_clusters(rows_path: Path, out_path: Path) -> dict[str, int]:
    """Group line_item rows by (fund_number, label prefix), aggregating
    revenue vs. expenditure totals via budget_side_from_section, and flag a
    cluster as 'paired' when it has nonzero totals on both sides -- the
    signature of a revenue/expense program pass-through (e.g. a grant
    revenue line paired with its recipient expenditure allocations).

    Also tags each cluster with a cluster_type (debt_service,
    grant_funded_capital_project, mixed_grant_program, grant_funded_program,
    allocation_program, personnel_or_benefits, general) derived from member
    rows' classify.categorize_line_item() categories plus the capital-dollar
    share of expenditure, a one-paragraph plain-English narrative (with an
    explanatory note for one-sided clusters), and the key revenue and
    expenditure line references (page/account/label/amount) so downstream
    evidence rendering doesn't have to say only "cluster_id=...".

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
        category = categorize_line_item(row.get("account", ""), label, budget_side)
        amount = parse_amount(row.get("budget_26_27", ""))
        if amount is not None:
            decimal_amount = Decimal(amount)
            key_line = _KeyLine(
                label=label,
                page=row.get("page_number", ""),
                account=row.get("account", ""),
                amount=decimal_amount,
            )
            if budget_side == "revenue":
                agg.revenue_total += decimal_amount
                if abs(decimal_amount) > abs(agg.key_revenue_line.amount) or not agg.key_revenue_line.label:
                    agg.key_revenue_line = key_line
            else:
                agg.expenditure_total += decimal_amount
                if category in CAPITAL_LIKE_CATEGORIES:
                    agg.capital_expenditure_total += decimal_amount
                if abs(decimal_amount) > abs(agg.key_expenditure_line.amount) or not agg.key_expenditure_line.label:
                    agg.key_expenditure_line = key_line

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
                    "capital_expenditure_total": str(agg.capital_expenditure_total),
                    "is_paired": "true" if is_paired else "false",
                    "line_item_count": agg.line_item_count,
                    "sample_labels": "; ".join(agg.sample_labels),
                    "cluster_type": cluster_type,
                    "narrative": _narrative_for_cluster(agg, cluster_type, is_paired),
                    "key_revenue_line": agg.key_revenue_line.render(),
                    "key_expenditure_line": agg.key_expenditure_line.render(),
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
    "ONE_SIDED_NOTE",
    "build_clusters",
    "cluster_id_for",
    "extract_label_prefix",
]
