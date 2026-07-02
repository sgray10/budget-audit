from __future__ import annotations

import csv
from datetime import date
from decimal import Decimal
from pathlib import Path

from budget_audit.findings import FUND_NAMES

# Funds that have been extracted, reviewed, and reconciled and are covered by
# this report. Pages 139+ (funds 143, 151, 171, 172, 202) have not yet been
# extracted -- see docs/backlog.md -- and must not be implied as covered.
SCOPE_FUNDS = [
    ("101", "General"),
    ("116", "Solid Waste/Sanitation"),
    ("122", "Drug Enforcement"),
    ("131", "Highway"),
    ("141", "General Purpose School"),
]
SCOPE_PAGES = "23-138"
NOT_YET_INCLUDED_FUNDS = [
    ("143", "School Nutrition -- not yet extracted"),
    ("151", "Debt Service -- not yet extracted"),
    ("171", "General Capital Projects -- not yet extracted"),
    ("172", "Community Development -- not yet extracted"),
    ("202", "Nursing Home -- not yet extracted"),
]

CATEGORY_TITLES = {
    "delta": "Material year-over-year changes",
    "salary": "Compensation lines needing explanation",
    "reconciliation": "Items that do not reconcile in this extraction",
}
CATEGORY_ORDER = ["delta", "salary", "reconciliation"]


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
    not_included_rows = [[fund, note] for fund, note in NOT_YET_INCLUDED_FUNDS]
    return (
        "## Scope\n\n"
        f"This report covers pages {SCOPE_PAGES} of the "
        "Weakley County Finance, Ways, and Means packet dated 2026-06-30, "
        f"across {len(SCOPE_FUNDS)} funds:\n\n"
        + markdown_table(["Fund", "Fund name", "Status"], scope_rows)
        + "\n\n"
        "The following funds appear later in the packet (pages 139+) and are "
        "**not yet included** in this report:\n\n"
        + markdown_table(["Fund", "Status"], not_included_rows)
        + "\n\n"
        "Findings and totals below should not be read as covering the full "
        "county budget."
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
) -> None:
    report_date = report_date or date.today()
    sections = [
        "# Weakley County Finance, Ways, and Means Packet -- 2026-06-30\n",
        f"_Generated {report_date.isoformat()}. This is a citizen-produced analysis of a public "
        "meeting packet, not an official county document. See docs/methodology.md for the "
        "extraction and review process._\n",
        render_scope_section(),
        render_reconciliation_section(reconcile_summaries),
        render_findings_section(findings_path),
        "## How to read this report\n\n"
        "This report uses neutral language deliberately: `unclear`, `needs explanation`, and "
        "`does not reconcile in this extraction` describe open questions, not conclusions. "
        "A finding here is a prompt for a public-records question, not an accusation. "
        "See docs/weakley-county.md for the project's public posture.\n",
    ]

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n\n".join(sections), encoding="utf-8")
