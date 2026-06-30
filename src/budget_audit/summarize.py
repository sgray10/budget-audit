from __future__ import annotations

import csv
import re
from collections import defaultdict
from pathlib import Path


COMPENSATION_RE = re.compile(
    r"salary|salaries|wage|wages|overtime|social security|retirement|medical insurance|medicare|payroll",
    re.IGNORECASE,
)


def parse_amount(value: str) -> int | None:
    value = value.strip()
    if not value:
        return None

    negative = value.startswith("(") and value.endswith(")")
    cleaned = value.strip("()").replace(",", "").replace("$", "")

    if not re.fullmatch(r"-?\d+", cleaned):
        return None

    amount = int(cleaned)
    return -amount if negative else amount


def budget_side_from_section(section_hint: str) -> str:
    normalized = section_hint.lower()
    if "revenue" in normalized:
        return "revenue"
    if "summary" in normalized:
        return "summary"
    return "expenditure"


def summarize_classified_ocr_rows(
    rows_path: Path,
    out_dir: Path,
) -> dict[str, int]:
    rows = list(csv.DictReader(rows_path.open(encoding="utf-8")))
    line_rows = [row for row in rows if row.get("row_type") == "line_item"]
    non_line_rows = [row for row in rows if row.get("row_type") != "line_item"]

    fund_totals: dict[tuple[str, str, str], int] = defaultdict(int)
    section_totals: dict[tuple[str, str, str, str], int] = defaultdict(int)
    comp_totals: dict[tuple[str, str, str], int] = defaultdict(int)
    non_line_totals: dict[tuple[str, str, str, str], int] = defaultdict(int)

    unparsed_amounts = 0

    for row in line_rows:
        amount = parse_amount(row["budget_26_27"])
        if amount is None:
            unparsed_amounts += 1
            continue

        budget_side = budget_side_from_section(row["section_hint"])
        fund_key = (row["fund_number"], row["fund_name"], budget_side)
        section_key = (
            row["fund_number"],
            row["fund_name"],
            budget_side,
            row["section_hint"],
        )

        fund_totals[fund_key] += amount
        section_totals[section_key] += amount

        if COMPENSATION_RE.search(row["label"]):
            comp_key = (row["fund_number"], row["fund_name"], row["label"])
            comp_totals[comp_key] += amount

    for row in non_line_rows:
        amount = parse_amount(row["budget_26_27"])
        if amount is None:
            continue

        key = (
            row["fund_number"],
            row["fund_name"],
            row.get("row_type", ""),
            row.get("label", ""),
        )
        non_line_totals[key] += amount

    out_dir.mkdir(parents=True, exist_ok=True)

    with (out_dir / "summary_by_fund.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["fund_number", "fund_name", "budget_side", "budget_26_27_total"])
        for (fund_number, fund_name, budget_side), total in sorted(fund_totals.items()):
            writer.writerow([fund_number, fund_name, budget_side, total])

    with (out_dir / "summary_by_section.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["fund_number", "fund_name", "budget_side", "section_hint", "budget_26_27_total"])
        for (fund_number, fund_name, budget_side, section_hint), total in sorted(section_totals.items()):
            writer.writerow([fund_number, fund_name, budget_side, section_hint, total])

    with (out_dir / "summary_compensation.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["fund_number", "fund_name", "label", "budget_26_27_total"])
        for (fund_number, fund_name, label), total in sorted(comp_totals.items()):
            writer.writerow([fund_number, fund_name, label, total])

    with (out_dir / "summary_non_line_items.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["fund_number", "fund_name", "row_type", "label", "budget_26_27_total"])
        for (fund_number, fund_name, row_type, label), total in sorted(non_line_totals.items()):
            writer.writerow([fund_number, fund_name, row_type, label, total])

    return {
        "rows": len(rows),
        "line_rows": len(line_rows),
        "non_line_rows": len(non_line_rows),
        "unparsed_amounts": unparsed_amounts,
    }
