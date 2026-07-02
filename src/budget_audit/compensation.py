from __future__ import annotations

import csv
import re
from collections import defaultdict
from pathlib import Path

from budget_audit.reconcile import parse_amount

# Category/benefit rollup phrases, optionally preceded by a short department
# code (e.g. "DGA", "+ISM", "=ITG", "1G" -- confirmed OCR/source prefixes in
# the reviewed data). These describe a category, not one person.
AGGREGATE_LABEL_RE = re.compile(
    r"^(salaries|salary\s*&?\s*wages?|other salaries.*|social security|medicare"
    r"|medicare liability|state retirement|retirement.*|medical insurance.*"
    r"|payroll|overtime.*|salary equity funds|salary suppl(ement)?s?)$",
    re.IGNORECASE,
)
PREFIXED_AGGREGATE_RE = re.compile(r"^[A-Z0-9=+~]{1,8}\s+(.+)$")

SMALL_DOLLAR_REVIEW_THRESHOLD = 3000


def classify_compensation_label(label: str, budget_26_27_amount: int | None) -> str:
    """Coarse, low-confidence heuristic: 'aggregate' (looks like a benefit or
    category rollup, not one person) or 'needs_review' (plausibly identifies
    an individual position, or is a small enough dollar amount to plausibly
    be one person's line item).

    This is a triage aid for human review, not a determination that any line
    item does or does not identify an individual. See docs/weakley-county.md
    'Public posture'.
    """
    stripped = label.strip()

    candidate = stripped
    prefix_match = PREFIXED_AGGREGATE_RE.match(stripped)
    if prefix_match:
        candidate = prefix_match.group(1)

    if AGGREGATE_LABEL_RE.match(candidate):
        return "aggregate"

    if budget_26_27_amount is not None and 0 < budget_26_27_amount <= SMALL_DOLLAR_REVIEW_THRESHOLD:
        return "needs_review"

    if re.search(r"salary|wage", candidate, re.IGNORECASE):
        return "needs_review"

    return "aggregate"


def analyze_compensation(
    rows_path: Path,
    out_dir: Path,
) -> dict[str, int]:
    """Roll up compensation-flagged rows by fund/department/division and
    apply the coarse individual-vs-aggregate heuristic.

    Writes compensation_rollup.csv (totals by fund/department/division) and
    compensation_flags.csv (one row per compensation line item with its
    heuristic classification, for manual review).
    """
    rows = list(csv.DictReader(rows_path.open(encoding="utf-8")))
    if not rows:
        raise ValueError(f"no rows found in {rows_path}")

    # contains_salary_or_compensation is page-level page-review metadata (set
    # by enrich.py for the whole page), not a per-row signal -- using it here
    # would pull in every row on a page that merely contains some compensation
    # line somewhere (e.g. "Office Supplies" on the same page as "Salaries").
    # category == "compensation" is the row-level classification and is the
    # correct filter.
    comp_rows = [row for row in rows if row.get("category") == "compensation"]

    rollup: dict[tuple[str, str, str, str], int] = defaultdict(int)
    flag_rows: list[dict[str, str]] = []
    unparsed = 0

    for row in comp_rows:
        amount = parse_amount(row.get("budget_26_27", ""))
        if amount is None:
            unparsed += 1

        classification = classify_compensation_label(row.get("label", ""), amount)

        fund_number = row.get("fund_number", "")
        fund_name = row.get("fund_name", "")
        department = row.get("department", "") or "(unspecified)"
        division = row.get("division", "") or "(unspecified)"

        if amount is not None:
            rollup[(fund_number, fund_name, department, division)] += amount

        flag_rows.append(
            {
                "document_id": row.get("document_id", ""),
                "page_number": row.get("page_number", ""),
                "fund_number": fund_number,
                "fund_name": fund_name,
                "department": department,
                "division": division,
                "account": row.get("account", ""),
                "label": row.get("label", ""),
                "budget_26_27": row.get("budget_26_27", ""),
                "classification": classification,
            }
        )

    out_dir.mkdir(parents=True, exist_ok=True)

    with (out_dir / "compensation_rollup.csv").open("w", newline="", encoding="utf-8") as handle:
        rollup_writer = csv.writer(handle)
        rollup_writer.writerow(["fund_number", "fund_name", "department", "division", "budget_26_27_total"])
        for (fund_number, fund_name, department, division), total in sorted(rollup.items()):
            rollup_writer.writerow([fund_number, fund_name, department, division, total])

    flag_fieldnames = list(flag_rows[0].keys()) if flag_rows else []
    with (out_dir / "compensation_flags.csv").open("w", newline="", encoding="utf-8") as handle:
        flag_writer = csv.DictWriter(handle, fieldnames=flag_fieldnames)
        flag_writer.writeheader()
        flag_writer.writerows(flag_rows)

    return {
        "compensation_rows": len(comp_rows),
        "needs_review_rows": sum(1 for row in flag_rows if row["classification"] == "needs_review"),
        "aggregate_rows": sum(1 for row in flag_rows if row["classification"] == "aggregate"),
        "unparsed_amounts": unparsed,
    }
