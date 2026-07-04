from __future__ import annotations

import csv
from datetime import date
from decimal import Decimal
from pathlib import Path

from budget_audit.findings import FUND_NAMES

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

CATEGORY_TITLES = {
    "grant_roll_on": "New grant/program revenue or expense",
    "grant_roll_off": "Grant/program revenue or expense dropping to zero",
    "capital_project": "Capital projects and large one-time purchases",
    "contracted_services": "Contracted services",
    "allocation_change": "Recipient/allocation changes",
    "personnel_change": "Compensation and benefit lines needing explanation",
    "needs_human_review": "Other material changes needing review",
    "reconciliation": "Items that do not reconcile in this extraction",
}
CATEGORY_ORDER = [
    "grant_roll_on",
    "grant_roll_off",
    "capital_project",
    "contracted_services",
    "allocation_change",
    "personnel_change",
    "needs_human_review",
    "reconciliation",
]
# Categories whose findings carry a specific public-records question template
# (see findings.PUBLIC_RECORDS_QUESTIONS) rather than a generic fallback --
# these are the ones worth surfacing in the public-records candidates section.
PUBLIC_RECORDS_CATEGORIES = [
    "grant_roll_on",
    "grant_roll_off",
    "capital_project",
    "contracted_services",
    "allocation_change",
    "personnel_change",
    "reconciliation",
]


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


def render_scope_section() -> str:
    scope_rows = [[fund, name, "reconciled"] for fund, name in SCOPE_FUNDS]
    return (
        "## Scope\n\n"
        f"This report covers pages {SCOPE_PAGES} of the "
        "Weakley County Finance, Ways, and Means packet dated 2026-06-30, "
        f"across {len(SCOPE_FUNDS)} funds:\n\n"
        + markdown_table(["Fund", "Fund name", "Status"], scope_rows)
        + "\n\n"
        "Findings and totals below cover the budget pages in this packet; they "
        "should not be read as covering records or budget documents outside "
        "the source packet."
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
    return {
        "fund_number": fund_number,
        "fund_name": FUND_NAMES.get(fund_number, fund_number),
        "revenue": metrics.get("revenue_with_transfers", ""),
        "expenditure": metrics.get("expenditure_with_transfers", ""),
        "net": metrics.get("net_with_transfers", ""),
    }


def render_reconciliation_section(reconcile_summaries: list[dict[str, str]]) -> str:
    rows = [
        [summary["fund_number"], summary["fund_name"], summary["revenue"], summary["expenditure"], summary["net"]]
        for summary in reconcile_summaries
    ]
    return "## Reconciliation summary\n\n" + markdown_table(
        ["Fund", "Fund name", "Revenue w/ transfers", "Expenditure w/ transfers", "Net"], rows
    )


def render_data_quality_section(data_quality_path: Path | None) -> str:
    if data_quality_path is None:
        return "## Data-quality warnings\n\nNo data-quality warnings were generated for this report.\n"

    rows = list(csv.DictReader(data_quality_path.open(encoding="utf-8")))
    if not rows:
        return "## Data-quality warnings\n\nNo data-quality warnings were generated for this report.\n"

    table_rows = [
        [
            row["warning_type"],
            row["severity"],
            row["confidence"],
            row["summary"],
            row["evidence"],
        ]
        for row in rows
    ]
    return "## Data-quality warnings\n\n" + markdown_table(
        ["Type", "Severity", "Confidence", "Summary", "Evidence"], table_rows
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


def render_top_changes_section(top_changes_path: Path | None) -> str:
    if top_changes_path is None:
        return "## Top changes\n\nNo top-change rankings were generated for this report.\n"

    rows = list(csv.DictReader(top_changes_path.open(encoding="utf-8")))
    absolute_rows = [row for row in rows if row["rank_type"] == "absolute"]
    percent_rows = [row for row in rows if row["rank_type"] == "percent"]

    sections = ["## Top changes\n"]
    if absolute_rows:
        sections.append("### Top absolute-dollar changes\n")
        sections.append(_top_change_table(absolute_rows))
    else:
        sections.append("### Top absolute-dollar changes\n\nNo absolute-dollar changes were ranked.\n")

    if percent_rows:
        sections.append("### Top percentage changes\n")
        sections.append(_top_change_table(percent_rows))
    else:
        sections.append(
            "### Top percentage changes\n\n"
            "No percentage changes cleared the minimum dollar guardrail for this report.\n"
        )

    return "\n\n".join(sections)


def render_top_clusters_section(clusters_path: Path | None, n: int = 10) -> str:
    if clusters_path is None:
        return "## Top clusters\n\nNo clusters were generated for this report.\n"

    rows = list(csv.DictReader(clusters_path.open(encoding="utf-8")))
    if not rows:
        return "## Top clusters\n\nNo clusters were generated for this report.\n"

    def magnitude(row: dict[str, str]) -> int:
        return abs(int(row["revenue_total"])) + abs(int(row["expenditure_total"]))

    top_rows = sorted(rows, key=magnitude, reverse=True)[:n]
    table_rows = [
        [
            row["fund_number"],
            row["prefix"],
            "yes" if row["is_paired"] == "true" else "no",
            row["revenue_total"],
            row["expenditure_total"],
            row["line_item_count"],
            row["sample_labels"],
        ]
        for row in top_rows
    ]
    return (
        "## Top clusters\n\n"
        "Line items sharing a fund and a short label prefix (e.g. a grant or program code), "
        "ranked by combined revenue+expenditure magnitude. A 'paired' cluster has nonzero "
        "totals on both the revenue and expenditure side, the signature of a program "
        "pass-through (grant revenue paired with recipient allocations) worth reviewing together "
        "rather than as isolated line items.\n\n"
        + markdown_table(
            ["Fund", "Prefix", "Paired", "Revenue total", "Expenditure total", "Line items", "Sample labels"],
            table_rows,
        )
    )


def render_public_records_section(findings_path: Path) -> str:
    rows = list(csv.DictReader(findings_path.open(encoding="utf-8")))
    candidates = [row for row in rows if row["category"] in PUBLIC_RECORDS_CATEGORIES]
    if not candidates:
        return "## Public-records question candidates\n\nNo public-records question candidates were generated for this report.\n"

    sections = ["## Public-records question candidates\n"]
    for item in candidates:
        sections.append(f"**{item['title']}**\n\n{item['open_questions']}\n")
    return "\n".join(sections)


def render_findings_section(findings_path: Path) -> str:
    rows = list(csv.DictReader(findings_path.open(encoding="utf-8")))
    if not rows:
        return "## Findings\n\nNo findings were generated for this report.\n"

    by_category: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        by_category.setdefault(row["category"], []).append(row)

    sections = ["## Findings\n"]
    for category in CATEGORY_ORDER:
        items = by_category.get(category, [])
        if not items:
            continue
        sections.append(f"### {CATEGORY_TITLES.get(category, category.title())}\n")
        for item in items:
            sections.append(
                f"**{item['title']}** _(confidence: {item['confidence']}, status: {item['status']})_\n\n"
                f"{item['summary']}\n\n"
                f"Source: {item['evidence']}\n\n"
                f"Open questions: {item['open_questions']}\n"
            )
    return "\n".join(sections)


def render_report(
    findings_path: Path,
    reconcile_summaries: list[dict[str, str]],
    out_path: Path,
    report_date: date | None = None,
    *,
    data_quality_path: Path | None = None,
    top_changes_path: Path | None = None,
    clusters_path: Path | None = None,
) -> None:
    report_date = report_date or date.today()
    sections = [
        "# Weakley County Finance, Ways, and Means Packet -- 2026-06-30\n",
        f"_Generated {report_date.isoformat()}. This is a citizen-produced analysis of a public "
        "meeting packet, not an official county document. See docs/methodology.md for the "
        "extraction and review process._\n",
        render_scope_section(),
        render_reconciliation_section(reconcile_summaries),
        render_data_quality_section(data_quality_path),
        render_top_clusters_section(clusters_path),
        render_top_changes_section(top_changes_path),
        render_findings_section(findings_path),
        render_public_records_section(findings_path),
        "## How to read this report\n\n"
        "This report uses neutral language deliberately: `unclear`, `needs explanation`, and "
        "`does not reconcile in this extraction` describe open questions, not conclusions. "
        "A finding here is a prompt for a public-records question, not an accusation. "
        "See docs/weakley-county.md for the project's public posture.\n",
    ]

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n\n".join(sections), encoding="utf-8")
