from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from budget_audit.data_quality import DataQualityWarning
from budget_audit.questions import questions_for_category
from budget_audit.structural_changes import GrantFundedCapitalPair, WholeFundChange

# Cluster types worth surfacing as a priority area on their own -- "general"
# and "personnel_or_benefits" clusters are common and usually unremarkable,
# so they're left to the ordinary findings-by-category section rather than
# competing for a spot in this short list.
NOTABLE_CLUSTER_TYPES = {
    "grant_funded_capital_project",
    "grant_funded_program",
    "allocation_program",
    "debt_service",
}

CLUSTER_TYPE_TO_QUESTION_CATEGORY = {
    "grant_funded_capital_project": "grant_funded_capital_project",
    "grant_funded_program": "grant_or_intergovernmental_revenue",
    "allocation_program": "allocation_or_recipient_payment",
    "debt_service": "debt_service",
}

MAX_PRIORITY_AREAS = 10


@dataclass(frozen=True)
class PriorityArea:
    priority_area_id: str
    title: str
    funds: list[str]
    why_it_matters: str
    dollar_amounts: str
    pattern: str
    questions: list[str]
    evidence: list[str]
    depends_on_manual_correction: bool = False


def _cluster_magnitude(row: dict[str, str]) -> int:
    try:
        return abs(int(row["revenue_total"])) + abs(int(row["expenditure_total"]))
    except ValueError:
        return 0


def _from_whole_fund_change(change: WholeFundChange) -> PriorityArea:
    direction_text = (
        "revenue and expenditure both drop to near zero in the proposed budget"
        if change.direction == "zeroed_out"
        else "revenue and expenditure both appear from near zero in the proposed budget"
    )
    return PriorityArea(
        priority_area_id=f"structural-{change.fund_number}",
        title=f"Fund {change.fund_number} {change.fund_name} fund-wide change",
        funds=[change.fund_number],
        why_it_matters=(
            f"This fund's {direction_text} (revenue {change.revenue_old} -> {change.revenue_new}; "
            f"expenditure {change.expenditure_old} -> {change.expenditure_new}). This is a whole-fund "
            f"pattern, not an isolated line item, and needs explanation before the fund can be assumed "
            f"to be simply smaller or larger."
        ),
        dollar_amounts=(
            f"revenue {change.revenue_old} -> {change.revenue_new}; "
            f"expenditure {change.expenditure_old} -> {change.expenditure_new}"
        ),
        pattern="structural_change",
        questions=questions_for_category("whole_fund_structural_change"),
        evidence=[f"fund={change.fund_number} {change.fund_name}"] + [f"sample_label={label}" for label in change.sample_labels],
    )


def _from_grant_capital_pair(pair: GrantFundedCapitalPair) -> PriorityArea:
    return PriorityArea(
        priority_area_id=f"grant-capital-{pair.fund_number}",
        title=f"Fund {pair.fund_number} {pair.fund_name}: {pair.revenue_label} / {pair.expenditure_label}",
        funds=[pair.fund_number],
        why_it_matters=(
            f"A grant/intergovernmental revenue increase ({pair.revenue_label}, +{pair.revenue_delta}) "
            f"appears alongside a capital-expense increase of comparable magnitude "
            f"({pair.expenditure_label}, +{pair.expenditure_delta}). This looks like a single "
            f"grant-funded capital project rather than two unrelated line items."
        ),
        dollar_amounts=f"revenue +{pair.revenue_delta}; expenditure +{pair.expenditure_delta}",
        pattern="paired_revenue_expense",
        questions=questions_for_category("grant_funded_capital_project"),
        evidence=[
            f"fund={pair.fund_number} {pair.fund_name}",
            f"revenue_label={pair.revenue_label}",
            f"expenditure_label={pair.expenditure_label}",
        ],
    )


def _from_cluster(row: dict[str, str]) -> PriorityArea:
    cluster_type = row["cluster_type"]
    question_category = CLUSTER_TYPE_TO_QUESTION_CATEGORY.get(cluster_type, "needs_human_review")
    pattern = "paired_revenue_expense" if row["is_paired"] == "true" else "one_sided"

    why_by_type = {
        "grant_funded_capital_project": (
            "This cluster pairs grant/intergovernmental revenue with capital expense of comparable "
            "scale -- likely a single project, not isolated line items."
        ),
        "grant_funded_program": (
            "This cluster pairs grant/intergovernmental revenue with program expenditure (largely "
            "personnel/benefits) -- likely a grant- or program-funded activity."
        ),
        "allocation_program": (
            "This cluster allocates funds to named external recipients -- worth confirming the "
            "authorizing program and how recipients were selected."
        ),
        "debt_service": (
            "This cluster is a debt-service obligation (principal and/or interest on notes or loans) -- "
            "worth confirming the underlying debt instrument, terms, and purpose."
        ),
    }

    return PriorityArea(
        priority_area_id=f"cluster-{row['cluster_id']}",
        title=f"Fund {row['fund_number']} {row['fund_name']}: {row['prefix']} cluster",
        funds=[row["fund_number"]],
        why_it_matters=why_by_type.get(cluster_type, row["narrative"]),
        dollar_amounts=f"revenue {row['revenue_total']}; expenditure {row['expenditure_total']}",
        pattern=pattern,
        questions=questions_for_category(question_category),
        evidence=[
            f"cluster_id={row['cluster_id']}",
            f"sample_labels={row['sample_labels']}",
        ],
    )


def _from_data_quality_group(fund_number: str, warnings: list[DataQualityWarning]) -> PriorityArea:
    warning_types = sorted({warning.warning_type for warning in warnings})
    return PriorityArea(
        priority_area_id=f"data-quality-{fund_number}",
        title=f"Fund {fund_number}: high-impact data-quality issues",
        funds=[fund_number],
        why_it_matters=(
            f"{len(warnings)} high-impact data-quality warning(s) in this fund ({', '.join(warning_types)}) "
            f"affect rows that also show up in top changes, priority clusters, or public-records "
            f"candidates. These should be resolved before the associated numbers are used in public claims."
        ),
        dollar_amounts="",
        pattern="data_quality_driven",
        questions=questions_for_category("data_quality"),
        evidence=[warning.warning_id for warning in warnings],
    )


def build_priority_areas(
    clusters_path: Path | None,
    whole_fund_changes: list[WholeFundChange],
    grant_capital_pairs: list[GrantFundedCapitalPair],
    high_impact_warnings: list[DataQualityWarning],
    manual_correction_funds: set[str] | None = None,
    limit: int = MAX_PRIORITY_AREAS,
) -> list[PriorityArea]:
    """Synthesize a short, ranked list of priority follow-up areas from
    clusters + top-dollar/structural signals + high-impact data-quality
    warnings -- not from every individual finding. See docs/report-design.md
    for why this stays a synthesis over existing structured outputs rather
    than a bespoke per-pattern generator.

    manual_correction_funds is the set of fund numbers with at least one
    manually-corrected row (see manual_corrections.py) -- used only to flag
    an area with the "depends on a traceable manual correction" note, at
    fund granularity rather than trying to match individual line items.
    """
    manual_correction_funds = manual_correction_funds or set()

    # "Headline" candidates -- whole-fund changes and fund-level grant/capital
    # pairs -- are always included and ranked by magnitude first; they are
    # each a single, large, self-contained story.
    headline: list[tuple[int, PriorityArea]] = []
    funds_with_grant_capital_pair: set[str] = set()
    for change in whole_fund_changes:
        magnitude = int(abs(change.revenue_old)) + int(abs(change.expenditure_old))
        headline.append((magnitude, _from_whole_fund_change(change)))
    for pair in grant_capital_pairs:
        magnitude = int(pair.revenue_delta) + int(pair.expenditure_delta)
        headline.append((magnitude, _from_grant_capital_pair(pair)))
        funds_with_grant_capital_pair.add(pair.fund_number)
    headline.sort(key=lambda item: item[0], reverse=True)

    # Cluster-derived candidates, bucketed by type. A cluster-level
    # grant_funded_capital_project for a fund that already has a fund-level
    # pair (a more precisely-named, dedicated signal) is skipped as a
    # near-duplicate of the same underlying story.
    debt_clusters: list[tuple[int, PriorityArea]] = []
    allocation_clusters: list[tuple[int, PriorityArea]] = []
    grant_program_clusters: list[tuple[int, PriorityArea]] = []
    if clusters_path is not None:
        cluster_rows = list(csv.DictReader(clusters_path.open(encoding="utf-8")))
        for row in cluster_rows:
            cluster_type = row["cluster_type"]
            if cluster_type not in NOTABLE_CLUSTER_TYPES:
                continue
            if cluster_type == "grant_funded_capital_project" and row["fund_number"] in funds_with_grant_capital_pair:
                continue
            magnitude = _cluster_magnitude(row)
            area = _from_cluster(row)
            if cluster_type == "debt_service":
                debt_clusters.append((magnitude, area))
            elif cluster_type == "allocation_program":
                allocation_clusters.append((magnitude, area))
            else:
                grant_program_clusters.append((magnitude, area))
    debt_clusters.sort(key=lambda item: item[0], reverse=True)
    allocation_clusters.sort(key=lambda item: item[0], reverse=True)
    grant_program_clusters.sort(key=lambda item: item[0], reverse=True)

    by_fund_dq: dict[str, list[DataQualityWarning]] = {}
    for warning in high_impact_warnings:
        if warning.fund_number:
            by_fund_dq.setdefault(warning.fund_number, []).append(warning)
    data_quality_areas = [
        _from_data_quality_group(fund_number, warnings) for fund_number, warnings in sorted(by_fund_dq.items())
    ]

    # Assemble in a fixed bucket order (headline stories first), but
    # guarantee at least a couple of slots each for debt-service and
    # recipient-allocation clusters and at least one data-quality slot when
    # they exist -- a pure dollar-magnitude sort would let a handful of
    # large grant/capital pairs crowd out smaller but still important
    # patterns entirely, which defeats the point of a *diverse* set of
    # follow-up areas.
    reserved_for_dq = 1 if data_quality_areas else 0
    ordered: list[PriorityArea] = [area for _magnitude, area in headline]
    ordered.extend(area for _magnitude, area in debt_clusters[:2])
    ordered.extend(area for _magnitude, area in allocation_clusters[:2])

    remaining_slots = max(limit - reserved_for_dq - len(ordered), 0)
    ordered.extend(area for _magnitude, area in grant_program_clusters[:remaining_slots])
    # Backfill with any debt/allocation clusters bumped by the initial cap,
    # if there's still room before the data-quality slot.
    leftover = debt_clusters[2:] + allocation_clusters[2:]
    leftover.sort(key=lambda item: item[0], reverse=True)
    remaining_slots = max(limit - reserved_for_dq - len(ordered), 0)
    ordered.extend(area for _magnitude, area in leftover[:remaining_slots])

    if data_quality_areas and len(ordered) < limit:
        ordered.append(data_quality_areas[0])

    areas: list[PriorityArea] = []
    for area in ordered[:limit]:
        depends_on_correction = any(fund in manual_correction_funds for fund in area.funds)
        areas.append(
            PriorityArea(
                priority_area_id=area.priority_area_id,
                title=area.title,
                funds=area.funds,
                why_it_matters=area.why_it_matters,
                dollar_amounts=area.dollar_amounts,
                pattern=area.pattern,
                questions=area.questions,
                evidence=area.evidence,
                depends_on_manual_correction=depends_on_correction,
            )
        )
    return areas


def write_priority_areas(areas: list[PriorityArea], out_path: Path) -> int:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "priority_area_id",
        "title",
        "funds",
        "why_it_matters",
        "dollar_amounts",
        "pattern",
        "questions",
        "evidence",
        "depends_on_manual_correction",
    ]
    with out_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for area in areas:
            writer.writerow(
                {
                    "priority_area_id": area.priority_area_id,
                    "title": area.title,
                    "funds": "; ".join(area.funds),
                    "why_it_matters": area.why_it_matters,
                    "dollar_amounts": area.dollar_amounts,
                    "pattern": area.pattern,
                    "questions": "; ".join(area.questions),
                    "evidence": "; ".join(area.evidence),
                    "depends_on_manual_correction": "true" if area.depends_on_manual_correction else "false",
                }
            )
    return len(areas)


__all__ = [
    "MAX_PRIORITY_AREAS",
    "PriorityArea",
    "build_priority_areas",
    "write_priority_areas",
]
