from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path

from budget_audit.reconcile import parse_amount

AMOUNT_FIELDS = ["actual_24_25", "budget_25_26", "actual_25_26", "budget_26_27"]
OCR_ARTIFACT_RE = re.compile(r"[§|{}\[\]<>]")

DATA_QUALITY_FIELDNAMES = [
    "warning_id",
    "warning_type",
    "severity",
    "confidence",
    "summary",
    "evidence",
    "status",
]


@dataclass(frozen=True)
class DataQualityWarning:
    warning_id: str
    warning_type: str
    severity: str
    confidence: str
    summary: str
    evidence: list[str]
    status: str = "needs_manual_verification"


def _row_ref(row: dict[str, str]) -> str:
    document_id = row.get("document_id", "")
    page_number = row.get("page_number", "")
    account = row.get("account", "")
    label = row.get("label", "")
    return f"{document_id}-p{page_number}-{account}-{label}".strip("-").lower().replace(" ", "-")[:90]


def _evidence(row: dict[str, str], extra: str) -> list[str]:
    return [
        f"document={row.get('document_id', '')}",
        f"page={row.get('page_number', '')}",
        f"fund={row.get('fund_number', '')} {row.get('fund_name', '')}".strip(),
        f"account={row.get('account', '')}",
        f"label={row.get('label', '')}",
        extra,
    ]


def data_quality_warnings_for_row(row: dict[str, str]) -> list[DataQualityWarning]:
    warnings: list[DataQualityWarning] = []
    row_ref = _row_ref(row)

    correction_action = row.get("correction_action", "")
    if correction_action:
        warnings.append(
            DataQualityWarning(
                warning_id=f"dq-manual-correction-{row_ref}",
                warning_type="manual_correction",
                severity="info",
                confidence="high",
                summary=(
                    "This row depends on a traceable manual correction. Review the correction "
                    "metadata before treating the extracted value as machine-read output."
                ),
                evidence=_evidence(row, f"correction_action={correction_action}"),
            )
        )

    label = row.get("label", "")
    raw_line = row.get("raw_line", "")
    if OCR_ARTIFACT_RE.search(label) or OCR_ARTIFACT_RE.search(raw_line):
        warnings.append(
            DataQualityWarning(
                warning_id=f"dq-ocr-artifact-{row_ref}",
                warning_type="ocr_artifact_text",
                severity="medium",
                confidence="medium",
                summary=(
                    "This row contains characters commonly introduced by OCR or table extraction. "
                    "Verify the label and values against the source page."
                ),
                evidence=_evidence(row, "artifact_source=label_or_raw_line"),
            )
        )

    if not row.get("fund_number", "") or not row.get("section_hint", ""):
        warnings.append(
            DataQualityWarning(
                warning_id=f"dq-missing-context-{row_ref}",
                warning_type="missing_context",
                severity="medium",
                confidence="high",
                summary=(
                    "This row is missing fund or section context, so downstream grouping may need "
                    "manual verification."
                ),
                evidence=_evidence(row, "missing=fund_number_or_section_hint"),
            )
        )

    for field in AMOUNT_FIELDS:
        raw_value = row.get(field, "")
        if not raw_value.strip():
            continue
        amount = parse_amount(raw_value)
        if amount is None:
            warnings.append(
                DataQualityWarning(
                    warning_id=f"dq-unparsed-amount-{field}-{row_ref}",
                    warning_type="unparsed_amount",
                    severity="high",
                    confidence="high",
                    summary=(
                        f"The {field} value could not be parsed as a whole-dollar amount. "
                        "Verify the amount against the source page before using this row."
                    ),
                    evidence=_evidence(row, f"{field}={raw_value}"),
                )
            )
        elif abs(amount) == 1:
            warnings.append(
                DataQualityWarning(
                    warning_id=f"dq-placeholder-amount-{field}-{row_ref}",
                    warning_type="placeholder_amount",
                    severity="low",
                    confidence="medium",
                    summary=(
                        f"The {field} value is $1 or -$1. This may be intentional, but it is "
                        "worth checking because placeholder-like values can distort percentage changes."
                    ),
                    evidence=_evidence(row, f"{field}={raw_value}"),
                )
            )

    return warnings


def write_data_quality_warnings(warnings: list[DataQualityWarning], out_path: Path) -> int:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=DATA_QUALITY_FIELDNAMES)
        writer.writeheader()
        for warning in warnings:
            writer.writerow(
                {
                    "warning_id": warning.warning_id,
                    "warning_type": warning.warning_type,
                    "severity": warning.severity,
                    "confidence": warning.confidence,
                    "summary": warning.summary,
                    "evidence": "; ".join(warning.evidence),
                    "status": warning.status,
                }
            )
    return len(warnings)


def analyze_data_quality(rows_path: Path, out_path: Path) -> dict[str, int]:
    rows = list(csv.DictReader(rows_path.open(encoding="utf-8")))
    if not rows:
        raise ValueError(f"no rows found in {rows_path}")

    warnings: list[DataQualityWarning] = []
    for row in rows:
        warnings.extend(data_quality_warnings_for_row(row))

    write_data_quality_warnings(warnings, out_path)

    return {
        "data_quality_warnings": len(warnings),
        "high_severity_warnings": sum(1 for warning in warnings if warning.severity == "high"),
    }
