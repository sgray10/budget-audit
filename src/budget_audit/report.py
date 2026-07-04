from __future__ import annotations

import csv
from datetime import date
from decimal import Decimal
from pathlib import Path

from budget_audit.clusters import ONE_SIDED_NOTE
from budget_audit.data_quality import HIGH_IMPACT_THRESHOLD
from budget_audit.findings import FUND_NAMES
from budget_audit.manual_corrections import ManualCorrectionSummary
from budget_audit.priority_areas import RELATED_ITEMS_PREFACE
from budget_audit.questions import dedupe_questions

# Funds that have been extracted, reviewed, and reconciled and are covered by
# this report for the 2026-06-30 Weakley County FWM packet.
SCOPE_FUNDS = [
    ("101", "General"),
    ("116", "Solid Waste/Sanitation"),
    ("122", "Drug Enforcement"),
    ("131", "Highway"),
    ("141", "General Purpose School"),
    ("143", "School Nutrition"),
    ("151", "Debt Service"),
    ("171", "General Capital Projects"),
    ("172", "Community Development"),
    ("202", "Nursing Home"),
]
SCOPE_PAGES = "23-158"

VERBOSITY_LEVELS = ("summary", "standard", "full")

CATEGORY_TITLES = {
    "insurance_or_claims": "Insurance and claims",
    "benefits_or_payroll_burden": "Benefits and payroll burden",
    "personnel": "Personnel",
    "debt_service": "Debt service",
    "grant_or_intergovernmental_revenue": "Grant and intergovernmental revenue",
    "capital_project": "Capital projects, equipment, and construction",
    "allocation_or_recipient_payment": "Allocations and recipient payments",
    "travel": "Travel",
    "communication": "Communication",
    "maintenance_services": "Maintenance services",
    "contracted_services": "Contracted services",
    "supplies_and_materials": "Supplies and materials",
    "whole_fund_structural_change": "Fund-wide structural changes",
    "grant_funded_capital_project": "Grant-funded capital projects",
    "needs_human_review": "Other material changes needing review",
    "reconciliation": "Items that do not reconcile in this extraction",
}
CATEGORY_ORDER = [
    "whole_fund_structural_change",
    "grant_funded_capital_project",
    "grant_or_intergovernmental_revenue",
    "allocation_or_recipient_payment",
    "debt_service",
    "capital_project",
    "insurance_or_claims",
    "benefits_or_payroll_burden",
    "personnel",
    "contracted_services",
    "maintenance_services",
    "travel",
    "communication",
    "supplies_and_materials",
    "needs_human_review",
    "reconciliation",
]
# Number of representative findings shown per category in the main-body
# "Findings by category" section -- the rest are in Appendix A, not omitted.
FINDINGS_SECTION_EXAMPLES_PER_CATEGORY = 3

RECONCILIATION_STATUS_LABELS = {
    "balanced_in_extraction": "Balanced in extraction (net is exactly zero)",
    "extracted_with_gap": "Extracted with a small gap relative to fund size",
    "needs_reconciliation_review": "Needs reconciliation review (gap is large relative to fund size)",
}
# A gap at or below this fraction of the fund's own revenue+expenditure scale
# (or at or below this flat dollar floor, whichever is larger) is treated as
# "small" -- everything above is flagged for review rather than silently
# called "reconciled". "Reconciled" is deliberately not used as a status
# value at all: this codebase's "reconcile" commands mean "extraction
# completed and totals compared," not "confirmed to balance."
SMALL_GAP_RATIO = Decimal("0.01")
SMALL_GAP_FLOOR = Decimal("1000")


def format_money(value: Decimal | None) -> str:
    if value is None:
        return ""
    return f"${value:,.2f}"


def markdown_table(headers: list[str], rows: list[list[str]]) -> str:
    """Render a simple markdown table."""
    out = ["| " + " | ".join(headers) + " |"]
    out.append("| " + " | ".join("---" for _ in headers) + " |")
    for row in rows:
        out.append("| " + " | ".join(row) + " |")
    return "\n".join(out)


def reconciliation_status(revenue: Decimal, expenditure: Decimal, net: Decimal) -> str:
    """Classify a fund's reconciliation gap without ever calling it
    'reconciled' -- that word implies a confirmed balance, which this
    OCR-derived extraction cannot claim on its own. See docs/report-design.md
    and the module docstring above for the four status values used.
    """
    if net == 0:
        return "balanced_in_extraction"
    scale = max(abs(revenue), abs(expenditure), Decimal("1"))
    ratio = abs(net) / scale
    if ratio <= SMALL_GAP_RATIO or abs(net) <= SMALL_GAP_FLOOR:
        return "extracted_with_gap"
    return "needs_reconciliation_review"


def render_scope_section() -> str:
    scope_rows = [[fund, name] for fund, name in SCOPE_FUNDS]
    return (
        "## Scope and limitations\n\n"
        f"This report covers pages {SCOPE_PAGES} of the "
        "Weakley County Finance, Ways, and Means packet dated 2026-06-30, "
        f"across {len(SCOPE_FUNDS)} funds:\n\n"
        + markdown_table(["Fund", "Fund name"], scope_rows)
        + "\n\n"
        "Findings and totals below cover the budget pages in this packet; they "
        "should not be read as covering records or budget documents outside "
        "the source packet. This report is machine-generated from OCR-extracted "
        "data and is a review queue, not a conclusion -- see 'How to read this "
        "report' at the end."
    )


def load_reconcile_summary(fund_number: str, path: Path) -> dict[str, str]:
    """Read one reconcile_fund_*.csv (metric,value pairs) into a summary row
    for the reconciliation table. Caller decides which of several possible
    reconcile files for a fund is authoritative -- this function does not
    guess between e.g. corrected vs stale variants.
    """
    reader = csv.reader(path.open(encoding="utf-8"))
    next(reader)  # header: "metric","value"
    metrics = {row[0]: row[1] for row in reader}
    revenue = Decimal(metrics.get("revenue_with_transfers", "0") or "0")
    expenditure = Decimal(metrics.get("expenditure_with_transfers", "0") or "0")
    net = Decimal(metrics.get("net_with_transfers", "0") or "0")
    return {
        "fund_number": fund_number,
        "fund_name": FUND_NAMES.get(fund_number, fund_number),
        "revenue": str(revenue),
        "expenditure": str(expenditure),
        "net": str(net),
        "status": reconciliation_status(revenue, expenditure, net),
        "revenue_line_items": metrics.get("revenue_line_items", ""),
        "transfer_in": metrics.get("transfer_in", ""),
        "expenditure_line_items": metrics.get("expenditure_line_items", ""),
        "transfer_out": metrics.get("transfer_out", ""),
        "unparsed_amounts": metrics.get("unparsed_amounts", ""),
    }


def render_reconciliation_section(reconcile_summaries: list[dict[str, str]]) -> str:
    rows = [
        [
            summary["fund_number"],
            summary["fund_name"],
            summary["revenue"],
            summary["expenditure"],
            summary["net"],
            RECONCILIATION_STATUS_LABELS.get(summary["status"], summary["status"]),
        ]
        for summary in reconcile_summaries
    ]

    balanced = [s for s in reconcile_summaries if s["status"] == "balanced_in_extraction"]
    small_gap = [s for s in reconcile_summaries if s["status"] == "extracted_with_gap"]
    needs_review = [s for s in reconcile_summaries if s["status"] == "needs_reconciliation_review"]

    interpretation_lines = [
        f"- {len(balanced)} fund(s) balance exactly in this extraction (net is exactly zero): "
        + (", ".join(f"Fund {s['fund_number']}" for s in balanced) if balanced else "none"),
        f"- {len(small_gap)} fund(s) extract with a small gap relative to fund size: "
        + (", ".join(f"Fund {s['fund_number']}" for s in small_gap) if small_gap else "none"),
        f"- {len(needs_review)} fund(s) show a gap large relative to fund size and need reconciliation "
        "review before being treated as balanced: "
        + (", ".join(f"Fund {s['fund_number']}" for s in needs_review) if needs_review else "none"),
    ]
    interpretation = (
        "A large gap may reflect an extraction error, a missing or misclassified line item, "
        "transfer handling, or a genuine imbalance in the source packet itself -- this report "
        "does not assume which. See the per-category findings and Appendix D for detail.\n\n"
        + "\n".join(interpretation_lines)
    )

    return (
        "## Reconciliation summary\n\n"
        + markdown_table(
            ["Fund", "Fund name", "Revenue w/ transfers", "Expenditure w/ transfers", "Net", "Status"], rows
        )
        + "\n\n"
        + interpretation
    )


def render_executive_summary(
    reconcile_summaries: list[dict[str, str]],
    priority_area_titles: list[str],
    high_impact_dq_count: int,
) -> str:
    fund_count = len(reconcile_summaries)
    needs_review = [s for s in reconcile_summaries if s["status"] == "needs_reconciliation_review"]
    gap_sentence = (
        "All funds extract cleanly or with only a small gap relative to fund size."
        if not needs_review
        else (
            f"{len(needs_review)} of {fund_count} funds show a reconciliation gap large enough to need "
            f"review before being treated as balanced (Fund(s) {', '.join(s['fund_number'] for s in needs_review)})."
        )
    )
    areas_sentence = (
        "No priority follow-up areas were identified from this packet."
        if not priority_area_titles
        else "The areas that most deserve review are: " + "; ".join(priority_area_titles) + "."
    )

    return (
        "## Executive summary\n\n"
        f"This report identifies review candidates from a public budget packet covering {fund_count} funds "
        f"across pages {SCOPE_PAGES}. {gap_sentence}\n\n"
        f"{areas_sentence}\n\n"
        "This report does not assert wrongdoing. Findings here are machine-generated review candidates, "
        "not conclusions -- many are ordinary grant, project, debt, or accounting mechanics that a records "
        "request or a conversation with the relevant department can explain in full. "
        f"{high_impact_dq_count} data-quality warning(s) in this report are high-impact enough that the "
        "underlying numbers should be verified against the source page before being used in any public "
        "claim; see 'High-impact data-quality warnings' below."
    )


def render_priority_areas_section(priority_areas_path: Path | None) -> str:
    if priority_areas_path is None:
        return "## Priority follow-up areas\n\nNo priority follow-up areas were generated for this report.\n"

    rows = list(csv.DictReader(priority_areas_path.open(encoding="utf-8")))
    if not rows:
        return "## Priority follow-up areas\n\nNo priority follow-up areas were generated for this report.\n"

    sections = ["## Priority follow-up areas\n"]
    pattern_labels = {
        "structural_change": "fund-wide structural change",
        "paired_revenue_expense": "paired revenue/expense",
        "one_sided": "one-sided (no offsetting revenue or expense found)",
        "data_quality_driven": "data-quality driven",
    }
    for rank, row in enumerate(rows, start=1):
        parts = [
            f"### {rank}. {row['title']}",
            f"**Funds:** {row['funds']} &nbsp;&nbsp; **Pattern:** {pattern_labels.get(row['pattern'], row['pattern'])}",
            row["why_it_matters"],
        ]
        if row.get("pattern") == "one_sided":
            parts.append(f"_{ONE_SIDED_NOTE}_")
        if row.get("why_normal"):
            parts.append(f"**Why this may be normal:** {row['why_normal']}")
        parts.append(f"**Dollar amounts:** {row['dollar_amounts'] or '(not applicable)'}")
        parts.append(f"**Questions:** {row['questions']}")
        if row.get("first_records_request"):
            parts.append(f"**Recommended first records request:** {row['first_records_request']}")
        if row.get("related_items"):
            related = row["related_items"].split(" | ")
            parts.append(
                f"**{RELATED_ITEMS_PREFACE}** (the packet alone does not confirm a connection):\n\n"
                + "\n".join(f"- {item}" for item in related)
            )
        evidence = row["evidence"].split(" | ")
        parts.append("Source/evidence:\n\n" + "\n".join(f"- {item}" for item in evidence))
        if row.get("depends_on_manual_correction") == "true":
            parts.append(
                "_This finding depends on a traceable manual correction; verify correction metadata "
                "before relying on it._"
            )
        sections.append("\n\n".join(parts) + "\n")
    return "\n".join(sections)


def render_top_clusters_section(
    clusters_path: Path | None,
    n: int = 10,
    narrative_n: int = 5,
    priority_cluster_ids: set[str] | None = None,
) -> str:
    """Render the top-clusters table plus narratives. Narratives cover the
    top narrative_n clusters by magnitude AND every cluster referenced by a
    priority follow-up area (priority_cluster_ids) -- a cluster important
    enough for the priority list should never be a bare table row.
    """
    if clusters_path is None:
        return "## Top clusters\n\nNo clusters were generated for this report.\n"

    rows = list(csv.DictReader(clusters_path.open(encoding="utf-8")))
    if not rows:
        return "## Top clusters\n\nNo clusters were generated for this report.\n"

    priority_cluster_ids = priority_cluster_ids or set()

    def magnitude(row: dict[str, str]) -> int:
        return abs(int(row["revenue_total"])) + abs(int(row["expenditure_total"]))

    ranked = sorted(rows, key=magnitude, reverse=True)
    top_rows = ranked[:n]
    table_rows = [
        [
            row["fund_number"],
            row["prefix"],
            row["cluster_type"],
            "yes" if row["is_paired"] == "true" else "no",
            row["revenue_total"],
            row["expenditure_total"],
            row["line_item_count"],
            row["sample_labels"],
        ]
        for row in top_rows
    ]
    table = markdown_table(
        ["Fund", "Prefix", "Type", "Paired", "Revenue total", "Expenditure total", "Line items", "Sample labels"],
        table_rows,
    )

    narrative_rows = list(top_rows[:narrative_n])
    narrative_ids = {row["cluster_id"] for row in narrative_rows}
    for row in ranked:
        if row["cluster_id"] in priority_cluster_ids and row["cluster_id"] not in narrative_ids:
            narrative_rows.append(row)
            narrative_ids.add(row["cluster_id"])

    narrative_lines = ["### What these clusters appear to represent\n"]
    for row in narrative_rows:
        narrative_lines.append(f"**Fund {row['fund_number']} / {row['prefix']}:** {row['narrative']}\n")

    return (
        "## Top clusters\n\n"
        "Line items sharing a fund and a short label prefix (e.g. a grant or program code), "
        "ranked by combined revenue+expenditure magnitude. A 'paired' cluster has nonzero "
        "totals on both the revenue and expenditure side, the signature of a program "
        "pass-through (grant revenue paired with recipient allocations) worth reviewing together "
        "rather than as isolated line items.\n\n"
        + table
        + "\n\n"
        + "\n".join(narrative_lines)
    )


def _top_change_table(rows: list[dict[str, str]]) -> str:
    table_rows = [
        [
            row["rank"],
            row["fund_number"],
            row["label"],
            row["old_value"],
            row["new_value"],
            row["absolute_delta"],
            row["percent_delta"],
            row["evidence"],
        ]
        for row in rows
    ]
    return markdown_table(
        ["Rank", "Fund", "Label", "Old", "New", "Delta", "Percent", "Evidence"],
        table_rows,
    )


def render_top_absolute_changes_section(top_changes_path: Path | None) -> str:
    if top_changes_path is None:
        return "## Top absolute-dollar changes\n\nNo top-change rankings were generated for this report.\n"
    rows = list(csv.DictReader(top_changes_path.open(encoding="utf-8")))
    absolute_rows = [row for row in rows if row["rank_type"] == "absolute"]
    if not absolute_rows:
        return "## Top absolute-dollar changes\n\nNo absolute-dollar changes were ranked.\n"
    return "## Top absolute-dollar changes\n\n" + _top_change_table(absolute_rows)


def render_top_percentage_changes_section(top_changes_path: Path | None) -> str:
    if top_changes_path is None:
        return "## Top percentage changes\n\nNo top-change rankings were generated for this report.\n"
    rows = list(csv.DictReader(top_changes_path.open(encoding="utf-8")))
    percent_rows = [row for row in rows if row["rank_type"] == "percent"]
    if not percent_rows:
        return (
            "## Top percentage changes\n\n"
            "No percentage changes cleared the minimum dollar guardrail for this report.\n"
        )
    return "## Top percentage changes\n\n" + _top_change_table(percent_rows)


def render_high_impact_data_quality_section(data_quality_path: Path | None) -> str:
    if data_quality_path is None:
        return "## High-impact data-quality warnings\n\nNo data-quality warnings were generated for this report.\n"

    rows = list(csv.DictReader(data_quality_path.open(encoding="utf-8")))
    high_impact = [row for row in rows if int(row.get("impact_score", "0") or "0") >= HIGH_IMPACT_THRESHOLD]
    if not high_impact:
        return (
            "## High-impact data-quality warnings\n\n"
            f"No data-quality warnings scored at or above this report's high-impact threshold "
            f"({HIGH_IMPACT_THRESHOLD}). {len(rows)} lower-impact warning(s) are in Appendix B.\n"
        )

    table_rows = [
        [row["warning_type"], row["severity"], row["confidence"], row["summary"], row["evidence"]]
        for row in high_impact
    ]
    return (
        "## High-impact data-quality warnings\n\n"
        f"{len(high_impact)} of {len(rows)} data-quality warnings scored high-impact -- affecting a "
        "top-dollar change, a priority follow-up area, or carrying high severity/confidence on their own. "
        "The remaining lower-impact warnings (including routine $1 placeholder amounts) are in Appendix B.\n\n"
        + markdown_table(["Type", "Severity", "Confidence", "Summary", "Evidence"], table_rows)
    )


def render_public_records_section(findings_path: Path) -> str:
    rows = list(csv.DictReader(findings_path.open(encoding="utf-8")))
    by_category: dict[str, list[str]] = {}
    for row in rows:
        by_category.setdefault(row["category"], []).extend(row["open_questions"].split("; "))

    if not by_category:
        return (
            "## Public-records question candidates\n\n"
            "No public-records question candidates were generated for this report.\n"
        )

    sections = ["## Public-records question candidates\n"]
    for category in CATEGORY_ORDER:
        questions = by_category.get(category)
        if not questions:
            continue
        deduped = dedupe_questions(questions)
        sections.append(f"**{CATEGORY_TITLES.get(category, category.title())}**\n\n" + "\n".join(f"- {q}" for q in deduped))
    return "\n\n".join(sections)


def render_findings_section(findings_path: Path, examples_per_category: int = FINDINGS_SECTION_EXAMPLES_PER_CATEGORY) -> str:
    rows = list(csv.DictReader(findings_path.open(encoding="utf-8")))
    if not rows:
        return "## Findings by category\n\nNo findings were generated for this report.\n"

    by_category: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        by_category.setdefault(row["category"], []).append(row)

    sections = ["## Findings by category\n"]
    for category in CATEGORY_ORDER:
        items = by_category.get(category, [])
        if not items:
            continue
        sections.append(f"### {CATEGORY_TITLES.get(category, category.title())} ({len(items)})\n")
        for item in items[:examples_per_category]:
            sections.append(
                f"**{item['title']}** _(confidence: {item['confidence']}, status: {item['status']})_\n\n"
                f"{item['summary']}\n\n"
                f"Source: {item['evidence']}\n"
            )
        if len(items) > examples_per_category:
            sections.append(
                f"_{len(items) - examples_per_category} more {CATEGORY_TITLES.get(category, category).lower()} "
                "finding(s) are in Appendix A._\n"
            )
    return "\n".join(sections)


def render_appendix_raw_findings(findings_path: Path) -> str:
    rows = list(csv.DictReader(findings_path.open(encoding="utf-8")))
    if not rows:
        return "## Appendix A: raw material-change findings\n\nNo findings were generated for this report.\n"
    table_rows = [
        [row["category"], row["title"], row["confidence"], row["status"], row["evidence"]] for row in rows
    ]
    return "## Appendix A: raw material-change findings\n\n" + markdown_table(
        ["Category", "Title", "Confidence", "Status", "Evidence"], table_rows
    )


def render_appendix_data_quality(data_quality_path: Path | None) -> str:
    if data_quality_path is None:
        return "## Appendix B: all data-quality warnings\n\nNo data-quality warnings were generated for this report.\n"
    rows = list(csv.DictReader(data_quality_path.open(encoding="utf-8")))
    if not rows:
        return "## Appendix B: all data-quality warnings\n\nNo data-quality warnings were generated for this report.\n"
    table_rows = [
        [row["warning_type"], row["severity"], row["confidence"], row["impact_score"], row["summary"], row["evidence"]]
        for row in rows
    ]
    return "## Appendix B: all data-quality warnings\n\n" + markdown_table(
        ["Type", "Severity", "Confidence", "Impact score", "Summary", "Evidence"], table_rows
    )


def render_appendix_manual_corrections(
    manual_corrections_summary: ManualCorrectionSummary | None,
    manual_corrections_path: Path | None,
) -> str:
    if manual_corrections_summary is None or manual_corrections_summary.total == 0:
        return "## Appendix C: manual corrections\n\nNo manual corrections were applied for this report.\n"

    by_fund_rows = [[fund, str(count)] for fund, count in manual_corrections_summary.by_fund.items()]
    by_action_rows = [[action, str(count)] for action, count in manual_corrections_summary.by_action.items()]

    sections = [
        "## Appendix C: manual corrections\n",
        f"{manual_corrections_summary.total} row(s) in this report depend on a traceable manual correction. "
        "Manual corrections fix OCR/extraction misses and are documented with a reason in the source data -- "
        "see docs/corrections.md.\n",
        "**By fund:**\n\n" + markdown_table(["Fund", "Corrections"], by_fund_rows),
        "**By action:**\n\n" + markdown_table(["Action", "Count"], by_action_rows),
    ]

    if manual_corrections_summary.high_impact:
        high_impact_rows = [
            [row["fund_number"], row["account"], row["label"], row["budget_26_27"], row["correction_action"]]
            for row in manual_corrections_summary.high_impact
        ]
        sections.append(
            "**High-impact corrections by dollar amount:**\n\n"
            + markdown_table(["Fund", "Account", "Label", "Budget 26-27", "Action"], high_impact_rows)
        )

    if manual_corrections_path is not None:
        rows = list(csv.DictReader(manual_corrections_path.open(encoding="utf-8")))
        if rows:
            full_rows = [
                [
                    row["fund_number"],
                    row["account"],
                    row["label"],
                    row["correction_action"],
                    row["correction_reason"],
                    row["budget_26_27"],
                ]
                for row in rows
            ]
            sections.append(
                "**All manual corrections:**\n\n"
                + markdown_table(
                    ["Fund", "Account", "Label", "Action", "Reason", "Budget 26-27"], full_rows
                )
            )

    return "\n\n".join(sections)


def render_appendix_reconciliation(reconcile_summaries: list[dict[str, str]]) -> str:
    rows = [
        [
            s["fund_number"],
            s["fund_name"],
            s["revenue_line_items"],
            s["transfer_in"],
            s["expenditure_line_items"],
            s["transfer_out"],
            s["unparsed_amounts"],
        ]
        for s in reconcile_summaries
    ]
    return "## Appendix D: reconciliation details\n\n" + markdown_table(
        [
            "Fund",
            "Fund name",
            "Revenue (line items)",
            "Transfer in",
            "Expenditure (line items)",
            "Transfer out",
            "Unparsed amounts",
        ],
        rows,
    )


def render_report(
    findings_path: Path,
    reconcile_summaries: list[dict[str, str]],
    out_path: Path,
    report_date: date | None = None,
    *,
    data_quality_path: Path | None = None,
    top_changes_path: Path | None = None,
    clusters_path: Path | None = None,
    priority_areas_path: Path | None = None,
    manual_corrections_summary: ManualCorrectionSummary | None = None,
    manual_corrections_path: Path | None = None,
    verbosity: str = "standard",
) -> None:
    if verbosity not in VERBOSITY_LEVELS:
        raise ValueError(f"verbosity must be one of {VERBOSITY_LEVELS}, got {verbosity!r}")

    report_date = report_date or date.today()

    priority_area_titles: list[str] = []
    priority_cluster_ids: set[str] = set()
    if priority_areas_path is not None:
        priority_rows = list(csv.DictReader(priority_areas_path.open(encoding="utf-8")))
        priority_area_titles = [row["title"] for row in priority_rows]
        priority_cluster_ids = {
            row["priority_area_id"].removeprefix("cluster-")
            for row in priority_rows
            if row["priority_area_id"].startswith("cluster-")
        }

    high_impact_dq_count = 0
    if data_quality_path is not None:
        dq_rows = list(csv.DictReader(data_quality_path.open(encoding="utf-8")))
        high_impact_dq_count = sum(
            1 for row in dq_rows if int(row.get("impact_score", "0") or "0") >= HIGH_IMPACT_THRESHOLD
        )

    sections = [
        "# Weakley County Finance, Ways, and Means Packet -- 2026-06-30\n",
        f"_Generated {report_date.isoformat()}. This is a citizen-produced analysis of a public "
        "meeting packet, not an official county document. See docs/methodology.md for the "
        "extraction and review process._\n",
        render_scope_section(),
        render_reconciliation_section(reconcile_summaries),
        render_executive_summary(reconcile_summaries, priority_area_titles, high_impact_dq_count),
        render_priority_areas_section(priority_areas_path),
    ]

    if verbosity != "summary":
        sections.extend(
            [
                render_top_clusters_section(clusters_path, priority_cluster_ids=priority_cluster_ids),
                render_top_absolute_changes_section(top_changes_path),
                render_top_percentage_changes_section(top_changes_path),
                render_high_impact_data_quality_section(data_quality_path),
                render_public_records_section(findings_path),
                render_findings_section(findings_path),
            ]
        )

    if verbosity == "full":
        sections.extend(
            [
                render_appendix_raw_findings(findings_path),
                render_appendix_data_quality(data_quality_path),
                render_appendix_manual_corrections(manual_corrections_summary, manual_corrections_path),
                render_appendix_reconciliation(reconcile_summaries),
            ]
        )

    sections.append(
        "## How to read this report\n\n"
        "This report uses neutral language deliberately: `unclear`, `needs explanation`, and "
        "`does not reconcile in this extraction` describe open questions, not conclusions. "
        "A finding here is a prompt for a public-records question, not an accusation. "
        "See docs/weakley-county.md for the project's public posture."
        + (
            "\n\nThis report was generated at the 'standard' verbosity level: appendices with the full "
            "raw findings, all data-quality warnings, all manual corrections, and detailed reconciliation "
            "metrics are omitted here. Regenerate with `--verbosity full` for the complete appendices."
            if verbosity == "standard"
            else ""
        )
        + (
            "\n\nThis report was generated at the 'summary' verbosity level: only the executive summary "
            "and priority follow-up areas are included. Regenerate with `--verbosity standard` or "
            "`--verbosity full` for clusters, top changes, data-quality warnings, findings, and appendices."
            if verbosity == "summary"
            else ""
        )
        + "\n",
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n\n".join(sections), encoding="utf-8")


__all__ = [
    "CATEGORY_ORDER",
    "CATEGORY_TITLES",
    "SCOPE_FUNDS",
    "SCOPE_PAGES",
    "VERBOSITY_LEVELS",
    "format_money",
    "load_reconcile_summary",
    "markdown_table",
    "reconciliation_status",
    "render_report",
]
