from __future__ import annotations

import csv
import re
from collections import Counter
from pathlib import Path
from typing import TypedDict

ROW_KEY_FIELDS = ["document_id", "page_number", "account", "label"]
CORRECTION_META_FIELDS = ["correction_action", "correction_reason", "correction_raw_line"]


class CorrectionStats(TypedDict):
    input_rows: int
    output_rows: int
    replaced: int
    added: int
    unmatched_replacements: list[str]
    ambiguous_extracted_matches: list[str]
    ambiguous_correction_keys: list[str]


def _normalize_key_part(value: str) -> str:
    """Whitespace-only normalization for row-key comparison: strip leading/
    trailing whitespace and collapse internal whitespace runs.

    Deliberately does NOT do fuzzy/edit-distance matching -- a corrections/
    audit tool silently misapplying a fix to the wrong row is worse than a
    loud failure. See docs/corrections.md.
    """
    return re.sub(r"\s+", " ", value.strip())


def row_key(row: dict[str, str]) -> tuple[str, str, str, str]:
    document_id, page_number, account, label = (
        _normalize_key_part(row.get(field, "")) for field in ROW_KEY_FIELDS
    )
    return (document_id, page_number, account, label)


def _format_key(key: tuple[str, str, str, str]) -> str:
    document_id, page_number, account, label = key
    return f"document_id={document_id} page={page_number} account={account} label={label!r}"


def apply_row_corrections(
    rows_path: Path,
    corrections_path: Path,
    out_path: Path,
    strict: bool = False,
) -> CorrectionStats:
    rows = list(csv.DictReader(rows_path.open(encoding="utf-8")))
    corrections = list(csv.DictReader(corrections_path.open(encoding="utf-8")))

    if not rows:
        raise ValueError(f"no rows found in {rows_path}")

    out_fieldnames = list(rows[0].keys())
    for field in CORRECTION_META_FIELDS:
        if field not in out_fieldnames:
            out_fieldnames.append(field)

    replace_corrections: dict[tuple[str, str, str, str], dict[str, str]] = {}
    ambiguous_correction_keys: list[str] = []
    seen_correction_keys: set[tuple[str, str, str, str]] = set()

    for correction in corrections:
        if correction.get("action") != "replace":
            continue
        key = row_key(correction)
        if key in seen_correction_keys:
            ambiguous_correction_keys.append(_format_key(key))
        seen_correction_keys.add(key)
        replace_corrections[key] = correction  # last-one-wins, preserved for backward compat

    extracted_key_counts: Counter[tuple[str, str, str, str]] = Counter(row_key(row) for row in rows)

    corrected_rows: list[dict[str, str]] = []
    replaced = 0
    added = 0
    ambiguous_extracted_keys: set[tuple[str, str, str, str]] = set()

    for row in rows:
        key = row_key(row)
        replacement = replace_corrections.get(key)

        if replacement is None:
            corrected = dict(row)
        elif extracted_key_counts[key] > 1:
            # Ambiguous: this correction's key matches more than one
            # extracted row. Don't guess which one it means -- report only.
            corrected = dict(row)
            ambiguous_extracted_keys.add(key)
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

    matched_keys = set(extracted_key_counts.keys())
    unmatched_replacements = [
        _format_key(key) for key in replace_corrections if key not in matched_keys
    ]
    ambiguous_extracted_matches = [_format_key(key) for key in sorted(ambiguous_extracted_keys)]

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
                "category": correction.get("category") or "operating",
                "row_type": correction.get("row_type") or "line_item",
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

    if strict and (unmatched_replacements or ambiguous_extracted_matches):
        problems = []
        if unmatched_replacements:
            problems.append(
                f"{len(unmatched_replacements)} unmatched replace correction(s): "
                + "; ".join(unmatched_replacements)
            )
        if ambiguous_extracted_matches:
            problems.append(
                f"{len(ambiguous_extracted_matches)} ambiguous extracted-row match(es): "
                + "; ".join(ambiguous_extracted_matches)
            )
        raise ValueError("apply_row_corrections found unresolved replace corrections: " + " | ".join(problems))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=out_fieldnames)
        writer.writeheader()
        writer.writerows(corrected_rows)

    return {
        "input_rows": len(rows),
        "output_rows": len(corrected_rows),
        "replaced": replaced,
        "added": added,
        "unmatched_replacements": unmatched_replacements,
        "ambiguous_extracted_matches": ambiguous_extracted_matches,
        "ambiguous_correction_keys": ambiguous_correction_keys,
    }
