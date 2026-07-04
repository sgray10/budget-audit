from __future__ import annotations

import csv
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from budget_audit.analyze import HEADLINE_TRANSITION

TOP_CHANGE_FIELDNAMES = [
    "rank_type",
    "rank",
    "document_id",
    "page_number",
    "fund_number",
    "fund_name",
    "budget_side",
    "department",
    "account",
    "label",
    "old_value",
    "new_value",
    "absolute_delta",
    "percent_delta",
    "status",
    "evidence",
]


@dataclass(frozen=True)
class TopChangeConfig:
    limit: int = 10
    min_absolute_for_percent_rank: Decimal = Decimal("5000")


def _to_decimal(value: str) -> Decimal | None:
    stripped = value.strip()
    if not stripped:
        return None
    return Decimal(stripped)


def _headline_rows(delta_rows_path: Path) -> list[dict[str, str]]:
    rows = list(csv.DictReader(delta_rows_path.open(encoding="utf-8")))
    if not rows:
        raise ValueError(f"no rows found in {delta_rows_path}")
    return [row for row in rows if row.get("transition") == HEADLINE_TRANSITION[2]]


def _ranked_output_row(row: dict[str, str], rank_type: str, rank: int) -> dict[str, str]:
    evidence = (
        f"document={row.get('document_id', '')}; "
        f"page={row.get('page_number', '')}; "
        f"fund={row.get('fund_number', '')} {row.get('fund_name', '')}; "
        f"account={row.get('account', '')}"
    )
    return {
        "rank_type": rank_type,
        "rank": str(rank),
        "document_id": row.get("document_id", ""),
        "page_number": row.get("page_number", ""),
        "fund_number": row.get("fund_number", ""),
        "fund_name": row.get("fund_name", ""),
        "budget_side": row.get("budget_side", ""),
        "department": row.get("department", ""),
        "account": row.get("account", ""),
        "label": row.get("label", ""),
        "old_value": row.get("old_value", ""),
        "new_value": row.get("new_value", ""),
        "absolute_delta": row.get("absolute_delta", ""),
        "percent_delta": row.get("percent_delta", ""),
        "status": row.get("status", ""),
        "evidence": evidence,
    }


def build_top_change_rows(
    delta_rows_path: Path,
    config: TopChangeConfig = TopChangeConfig(),
) -> list[dict[str, str]]:
    headline_rows = _headline_rows(delta_rows_path)

    rows_with_absolute = [
        (row, absolute)
        for row in headline_rows
        if (absolute := _to_decimal(row.get("absolute_delta", ""))) is not None and absolute != 0
    ]
    top_absolute = sorted(rows_with_absolute, key=lambda item: abs(item[1]), reverse=True)[: config.limit]

    percent_candidates = [
        (row, percent, absolute)
        for row, absolute in rows_with_absolute
        if abs(absolute) >= config.min_absolute_for_percent_rank
        if (percent := _to_decimal(row.get("percent_delta", ""))) is not None
    ]
    top_percent = sorted(percent_candidates, key=lambda item: abs(item[1]), reverse=True)[: config.limit]

    output_rows: list[dict[str, str]] = []
    for rank, (row, _absolute) in enumerate(top_absolute, start=1):
        output_rows.append(_ranked_output_row(row, "absolute", rank))
    for rank, (row, _percent, _absolute) in enumerate(top_percent, start=1):
        output_rows.append(_ranked_output_row(row, "percent", rank))
    return output_rows


def write_top_changes(rows: list[dict[str, str]], out_path: Path) -> int:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=TOP_CHANGE_FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


def analyze_top_changes(
    delta_rows_path: Path,
    out_path: Path,
    config: TopChangeConfig = TopChangeConfig(),
) -> dict[str, int]:
    top_rows = build_top_change_rows(delta_rows_path, config)
    write_top_changes(top_rows, out_path)
    return {
        "top_change_rows": len(top_rows),
        "top_absolute_rows": sum(1 for row in top_rows if row["rank_type"] == "absolute"),
        "top_percent_rows": sum(1 for row in top_rows if row["rank_type"] == "percent"),
    }
