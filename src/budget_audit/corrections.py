from __future__ import annotations

import csv
from pathlib import Path

ROW_KEY_FIELDS = ["document_id", "page_number", "account", "label"]
CORRECTION_META_FIELDS = ["correction_action", "correction_reason", "correction_raw_line"]


def row_key(row: dict[str, str]) -> tuple[str, str, str, str]:
    return tuple(row.get(field, "") for field in ROW_KEY_FIELDS)


def apply_row_corrections(rows_path: Path, corrections_path: Path, out_path: Path) -> dict[str, int]:
    rows = list(csv.DictReader(rows_path.open(encoding="utf-8")))
    corrections = list(csv.DictReader(corrections_path.open(encoding="utf-8")))

    if not rows:
        raise ValueError(f"no rows found in {rows_path}")

    out_fieldnames = list(rows[0].keys())
    for field in CORRECTION_META_FIELDS:
        if field not in out_fieldnames:
            out_fieldnames.append(field)

    replace_corrections = {
        row_key(correction): correction
        for correction in corrections
        if correction.get("action") == "replace"
    }

    corrected_rows: list[dict[str, str]] = []
    replaced = 0
    added = 0

    for row in rows:
        replacement = replace_corrections.get(row_key(row))
        if replacement is None:
            corrected = dict(row)
        else:
            corrected = dict(row)
            for field in [
                "fund_number",
                "section_hint",
                "account",
                "label",
                "actual_24_25",
                "budget_25_26",
                "actual_25_26",
                "budget_26_27",
                "raw_line",
            ]:
                if field in replacement and replacement[field] != "":
                    corrected[field] = replacement[field]
            corrected["correction_action"] = "replace"
            corrected["correction_reason"] = replacement.get("reason", "")
            corrected["correction_raw_line"] = replacement.get("raw_line", "")
            replaced += 1

        for field in CORRECTION_META_FIELDS:
            corrected.setdefault(field, "")
        corrected_rows.append(corrected)

    for correction in corrections:
        if correction.get("action") != "add":
            continue

        added_row = {field: "" for field in out_fieldnames}
        added_row.update(
            {
                "document_id": correction.get("document_id", ""),
                "page_number": correction.get("page_number", ""),
                "line_number": correction.get("line_number", ""),
                "context_hint": "manual_correction",
                "category": "operating",
                "row_type": "line_item",
                "review_confidence": "manual",
                "contains_salary_or_compensation": "false",
                "contains_budget_table": "true",
                "division": "",
                "department": "",
                "fund_name": "",
                "fund_number": correction.get("fund_number", ""),
                "page_type": "budget_table",
                "section_hint": correction.get("section_hint", ""),
                "account": correction.get("account", ""),
                "label": correction.get("label", ""),
                "actual_24_25": correction.get("actual_24_25", ""),
                "budget_25_26": correction.get("budget_25_26", ""),
                "actual_25_26": correction.get("actual_25_26", ""),
                "budget_26_27": correction.get("budget_26_27", ""),
                "parse_status": "manual_correction",
                "raw_line": correction.get("raw_line", ""),
                "correction_action": "add",
                "correction_reason": correction.get("reason", ""),
                "correction_raw_line": correction.get("raw_line", ""),
            }
        )
        corrected_rows.append(added_row)
        added += 1

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=out_fieldnames)
        writer.writeheader()
        writer.writerows(corrected_rows)

    return {"input_rows": len(rows), "output_rows": len(corrected_rows), "replaced": replaced, "added": added}
