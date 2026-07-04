from __future__ import annotations

import csv
import re
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path

from budget_audit.reconcile import parse_amount

AMOUNT_FIELDS = ["actual_24_25", "budget_25_26", "actual_25_26", "budget_26_27"]
OCR_ARTIFACT_RE = re.compile(r"[§|{}\[\]<>]")

# Corrupted-label heuristics, validated against the full real dataset before
# being chosen: across 657 distinct labels, these two rules flag exactly the
# two genuinely OCR-mangled ones ("CRD Other State lal eral Development" --
# broken-word lowercase fragments -- and "tisa 'N Investment yore
# Achievement" -- a stray quote artifact) and nothing else. Kept
# deliberately narrow: a false "this label is corrupted" is itself a
# credibility problem for the report.
CORRUPTED_QUOTE_ARTIFACT_RE = re.compile(r"(?:^|\s)['\"][A-Za-z](?:\s|$)")
CORRUPTED_FRAGMENT_FUNCTION_WORDS = {
    "a", "an", "and", "as", "at", "by", "co", "de", "etc", "for", "from", "if",
    "in", "is", "non", "of", "on", "or", "per", "post", "pre", "re", "the",
    "to", "via", "vs", "w", "with",
}


def _lowercase_fragment(label: str) -> str | None:
    """A lowercase-only token of 2-5 letters amid a Title Case label, not a
    known function word -- e.g. the 'lal'/'eral' fragments OCR leaves when it
    splits a word like 'Rural'/'General' across whitespace.
    """
    tokens = label.split()
    if sum(1 for token in tokens if token[:1].isupper()) < 2:
        return None
    for token in tokens:
        bare = token.strip(".,;:()'\"-&/")
        if bare and bare.islower() and bare not in CORRUPTED_FRAGMENT_FUNCTION_WORDS and 2 <= len(bare) <= 5:
            return bare
    return None


def label_corruption_reason(label: str) -> str | None:
    if CORRUPTED_QUOTE_ARTIFACT_RE.search(label):
        return "quote_artifact"
    fragment = _lowercase_fragment(label)
    if fragment is not None:
        return f"lowercase_fragment={fragment}"
    return None

DATA_QUALITY_FIELDNAMES = [
    "warning_id",
    "warning_type",
    "severity",
    "confidence",
    "summary",
    "evidence",
    "status",
    "document_id",
    "page_number",
    "fund_number",
    "account",
    "amount",
    "impact_score",
]

# Weights are deliberately coarse -- this score ranks warnings for what
# belongs in the report's main body vs. Appendix B, it is not a precision
# instrument. Severity dominates; everything else nudges the ranking.
SEVERITY_WEIGHT = {"high": 30, "medium": 20, "low": 10, "info": 0}
CONFIDENCE_WEIGHT = {"high": 10, "medium": 6, "low": 3}
LARGE_AMOUNT_FLOOR = Decimal("5000")
MEDIUM_AMOUNT_FLOOR = Decimal("1000")

# A warning at or above this combined score is "high-impact": surfaced in
# the report's main body rather than only in Appendix B. Chosen so that a
# bare severity=medium/confidence=medium warning ($20+6=26) stays out, but
# the same warning affecting a top-dollar change, a priority cluster, or a
# public-records candidate (any one of which adds 15-20) clears the bar.
HIGH_IMPACT_THRESHOLD = 40


@dataclass(frozen=True)
class DataQualityWarning:
    warning_id: str
    warning_type: str
    severity: str
    confidence: str
    summary: str
    evidence: list[str]
    status: str = "needs_manual_verification"
    # Structured identifiers, kept alongside the human-readable evidence
    # list so a warning can be cross-referenced against top_changes.csv,
    # clusters.csv, and findings.csv without re-parsing evidence strings.
    document_id: str = ""
    page_number: str = ""
    fund_number: str = ""
    account: str = ""
    amount: Decimal | None = None


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


def _row_amount(row: dict[str, str]) -> Decimal | None:
    """Best-effort dollar amount for a row, preferring the headline
    budget_26_27 column -- used only to weight impact scoring, not as a
    substitute for the row's own parsed amount fields.
    """
    amount = parse_amount(row.get("budget_26_27", ""))
    if amount is None:
        amount = parse_amount(row.get("actual_25_26", ""))
    return None if amount is None else Decimal(amount)


def data_quality_warnings_for_row(row: dict[str, str]) -> list[DataQualityWarning]:
    warnings: list[DataQualityWarning] = []
    row_ref = _row_ref(row)
    document_id = row.get("document_id", "")
    page_number = row.get("page_number", "")
    fund_number = row.get("fund_number", "")
    account = row.get("account", "")
    amount_for_scoring = _row_amount(row)

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
                document_id=document_id,
                page_number=page_number,
                fund_number=fund_number,
                account=account,
                amount=amount_for_scoring,
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
                document_id=document_id,
                page_number=page_number,
                fund_number=fund_number,
                account=account,
                amount=amount_for_scoring,
            )
        )

    if row.get("row_type") == "line_item":
        corruption_reason = label_corruption_reason(label)
        if corruption_reason is not None:
            warnings.append(
                DataQualityWarning(
                    warning_id=f"dq-corrupted-label-{row_ref}",
                    warning_type="ocr_corrupted_label",
                    severity="medium",
                    confidence="medium",
                    summary=(
                        "This row's label appears OCR-corrupted (broken word fragments or stray "
                        "quote artifacts). The intended label likely exists on the source page; "
                        "verify it before quoting this line in public-facing analysis."
                    ),
                    evidence=_evidence(row, f"corruption={corruption_reason}"),
                    document_id=document_id,
                    page_number=page_number,
                    fund_number=fund_number,
                    account=account,
                    amount=amount_for_scoring,
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
                document_id=document_id,
                page_number=page_number,
                fund_number=fund_number,
                account=account,
                amount=amount_for_scoring,
            )
        )

    for amount_field in AMOUNT_FIELDS:
        raw_value = row.get(amount_field, "")
        if not raw_value.strip():
            continue
        amount = parse_amount(raw_value)
        if amount is None:
            warnings.append(
                DataQualityWarning(
                    warning_id=f"dq-unparsed-amount-{amount_field}-{row_ref}",
                    warning_type="unparsed_amount",
                    severity="high",
                    confidence="high",
                    summary=(
                        f"The {amount_field} value could not be parsed as a whole-dollar amount. "
                        "Verify the amount against the source page before using this row."
                    ),
                    evidence=_evidence(row, f"{amount_field}={raw_value}"),
                    document_id=document_id,
                page_number=page_number,
                fund_number=fund_number,
                account=account,
                amount=amount_for_scoring,
                )
            )
        elif abs(amount) == 1:
            warnings.append(
                DataQualityWarning(
                    warning_id=f"dq-placeholder-amount-{amount_field}-{row_ref}",
                    warning_type="placeholder_amount",
                    severity="low",
                    confidence="medium",
                    summary=(
                        f"The {amount_field} value is $1 or -$1. This may be intentional, but it is "
                        "worth checking because placeholder-like values can distort percentage changes."
                    ),
                    evidence=_evidence(row, f"{amount_field}={raw_value}"),
                    document_id=document_id,
                page_number=page_number,
                fund_number=fund_number,
                account=account,
                amount=amount_for_scoring,
                )
            )

    return warnings


@dataclass(frozen=True)
class ImpactContext:
    """Cross-reference sets built once from the rest of a report run and
    passed into data_quality_impact_score(), so this module doesn't need to
    import top_changes/clusters/findings itself. Empty by default -- a
    warning scored with no context still gets a severity/confidence-only
    score, it just won't clear HIGH_IMPACT_THRESHOLD from those alone unless
    severity is already high.
    """

    top_change_keys: frozenset[tuple[str, str, str]] = field(default_factory=frozenset)
    priority_fund_numbers: frozenset[str] = field(default_factory=frozenset)
    public_records_keys: frozenset[tuple[str, str, str]] = field(default_factory=frozenset)


# Warning types indicating the *label text itself* is unreliable -- a
# corrupted label on a large-dollar or top-priority row is escalated harder
# than the same corruption on a minor line, because the report is about to
# quote that label to a reader.
LABEL_CORRUPTION_TYPES = {"ocr_corrupted_label", "ocr_artifact_text"}


def data_quality_impact_score(warning: DataQualityWarning, context: ImpactContext = ImpactContext()) -> int:
    score = SEVERITY_WEIGHT.get(warning.severity, 0) + CONFIDENCE_WEIGHT.get(warning.confidence, 0)

    large_amount = warning.amount is not None and abs(warning.amount) >= LARGE_AMOUNT_FLOOR
    if warning.amount is not None:
        if large_amount:
            score += 15
        elif abs(warning.amount) >= MEDIUM_AMOUNT_FLOOR:
            score += 5

    key = (warning.document_id, warning.page_number, warning.account)
    if key in context.top_change_keys:
        score += 20
    if key in context.public_records_keys:
        score += 15
    if warning.fund_number and warning.fund_number in context.priority_fund_numbers:
        score += 10

    # A corrupted label attached to a big number is worse than either signal
    # alone -- e.g. "tisa 'N Investment yore Achievement" carrying a $33M
    # value in the top absolute-dollar changes, or "CRD Other State lal eral
    # Development" anchoring a priority follow-up area.
    if warning.warning_type in LABEL_CORRUPTION_TYPES and large_amount:
        score += 10

    return score


def is_high_impact(score: int) -> bool:
    return score >= HIGH_IMPACT_THRESHOLD


def write_data_quality_warnings(
    warnings: list[DataQualityWarning], out_path: Path, context: ImpactContext = ImpactContext()
) -> int:
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
                    "document_id": warning.document_id,
                    "page_number": warning.page_number,
                    "fund_number": warning.fund_number,
                    "account": warning.account,
                    "amount": "" if warning.amount is None else str(warning.amount),
                    "impact_score": data_quality_impact_score(warning, context),
                }
            )
    return len(warnings)


def compute_warnings(rows_path: Path) -> list[DataQualityWarning]:
    """The in-memory warning list, exposed separately from
    analyze_data_quality() so callers that need to build cross-reference
    context (e.g. priority_areas.py's high-impact-warnings input) don't have
    to re-parse the written CSV back into DataQualityWarning objects.
    """
    rows = list(csv.DictReader(rows_path.open(encoding="utf-8")))
    if not rows:
        raise ValueError(f"no rows found in {rows_path}")

    warnings: list[DataQualityWarning] = []
    for row in rows:
        warnings.extend(data_quality_warnings_for_row(row))
    return warnings


def analyze_data_quality(
    rows_path: Path, out_path: Path, context: ImpactContext = ImpactContext()
) -> dict[str, int]:
    warnings = compute_warnings(rows_path)
    write_data_quality_warnings(warnings, out_path, context)

    high_impact = sum(1 for warning in warnings if is_high_impact(data_quality_impact_score(warning, context)))

    return {
        "data_quality_warnings": len(warnings),
        "high_severity_warnings": sum(1 for warning in warnings if warning.severity == "high"),
        "high_impact_warnings": high_impact,
    }
