from __future__ import annotations

import csv
import re
from collections import defaultdict
from pathlib import Path


SOURCE = Path("data/processed/ocr_table_rows_enriched.csv")
OUT_FUND = Path("data/processed/summary_by_fund.csv")
OUT_SECTION = Path("data/processed/summary_by_section.csv")
OUT_COMP = Path("data/processed/summary_compensation.csv")


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


def fmt(value: int) -> str:
    return f"{value:,}"


rows = list(csv.DictReader(SOURCE.open(encoding="utf-8")))

fund_totals: dict[tuple[str, str], int] = defaultdict(int)
section_totals: dict[tuple[str, str, str], int] = defaultdict(int)
comp_totals: dict[tuple[str, str, str], int] = defaultdict(int)

unparsed_amounts = []

for row in rows:
    amount = parse_amount(row["budget_26_27"])
    if amount is None:
        unparsed_amounts.append(row)
        continue

    fund_key = (row["fund_number"], row["fund_name"])
    section_key = (row["fund_number"], row["fund_name"], row["section_hint"])

    fund_totals[fund_key] += amount
    section_totals[section_key] += amount

    if COMPENSATION_RE.search(row["label"]):
        comp_key = (row["fund_number"], row["fund_name"], row["label"])
        comp_totals[comp_key] += amount


OUT_FUND.parent.mkdir(parents=True, exist_ok=True)

with OUT_FUND.open("w", newline="", encoding="utf-8") as handle:
    writer = csv.writer(handle)
    writer.writerow(["fund_number", "fund_name", "budget_26_27_total"])
    for (fund_number, fund_name), total in sorted(fund_totals.items()):
        writer.writerow([fund_number, fund_name, total])

with OUT_SECTION.open("w", newline="", encoding="utf-8") as handle:
    writer = csv.writer(handle)
    writer.writerow(["fund_number", "fund_name", "section_hint", "budget_26_27_total"])
    for (fund_number, fund_name, section_hint), total in sorted(section_totals.items()):
        writer.writerow([fund_number, fund_name, section_hint, total])

with OUT_COMP.open("w", newline="", encoding="utf-8") as handle:
    writer = csv.writer(handle)
    writer.writerow(["fund_number", "fund_name", "label", "budget_26_27_total"])
    for (fund_number, fund_name, label), total in sorted(comp_totals.items()):
        writer.writerow([fund_number, fund_name, label, total])

print(f"rows: {len(rows)}")
print(f"unparsed budget_26_27 amounts: {len(unparsed_amounts)}")
print(f"wrote {OUT_FUND}")
print(f"wrote {OUT_SECTION}")
print(f"wrote {OUT_COMP}")

print("\nFund totals:")
for (fund_number, fund_name), total in sorted(fund_totals.items()):
    print(f"  {fund_number} {fund_name}: {fmt(total)}")

print("\nTop compensation labels:")
for (fund_number, fund_name, label), total in sorted(comp_totals.items(), key=lambda item: item[1], reverse=True)[:25]:
    print(f"  {fund_number} {fund_name} | {label}: {fmt(total)}")
