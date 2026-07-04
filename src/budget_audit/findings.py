from __future__ import annotations

import csv
from pathlib import Path

from budget_audit.models import Finding

FUND_NAMES = {
    "101": "General",
    "116": "Solid Waste/Sanitation",
    "122": "Drug Enforcement",
    "131": "Highway",
    "141": "General Purpose School",
    "143": "School Nutrition",
    "151": "Debt Service",
    "171": "General Capital Projects",
    "172": "Community Development",
    "202": "Nursing Home",
}

HEADLINE_TRANSITION_LABEL = "headline_actual_25_26_to_budget_26_27"


def _finding_id(prefix: str, *parts: str) -> str:
    slug = "-".join(part.strip().lower().replace(" ", "-").replace("/", "-") for part in parts if part)
    return f"{prefix}-{slug}"[:120]


def findings_from_deltas(delta_rows_path: Path) -> list[Finding]:
    """Build one Finding per material, new, or eliminated line item on the
    headline actual_25_26 -> budget_26_27 transition. Non-headline transitions
    are analytical detail (see line_item_deltas.csv), not surfaced here, so a
    single line item does not produce up to four duplicate findings.
    """
    rows = list(csv.DictReader(delta_rows_path.open(encoding="utf-8")))
    findings: list[Finding] = []

    for row in rows:
        if row["transition"] != HEADLINE_TRANSITION_LABEL:
            continue
        if row["status"] == "blank_both":
            continue
        surfaced = row["status"] in ("new", "eliminated") or row["material"] == "true"
        if not surfaced:
            continue

        fund_number = row["fund_number"]
        fund_name = row["fund_name"] or FUND_NAMES.get(fund_number, fund_number)
        label = row["label"]
        old_value = row["old_value"] or "(none)"
        new_value = row["new_value"] or "(none)"
        percent = row["percent_delta"]

        if row["status"] == "new":
            title = f"New line item: {label} (Fund {fund_number})"
            summary = (
                f"'{label}' in Fund {fund_number} {fund_name} does not appear in the "
                f"FY 2025-26 actual column but is present in the FY 2026-27 proposed "
                f"budget at {new_value}. This needs explanation: it may be a new "
                f"program, a renamed or reclassified line, or an extraction gap."
            )
        elif row["status"] == "eliminated":
            title = f"Eliminated line item: {label} (Fund {fund_number})"
            summary = (
                f"'{label}' in Fund {fund_number} {fund_name} was present in the "
                f"FY 2025-26 actual column at {old_value} but does not appear in the "
                f"FY 2026-27 proposed budget. This needs explanation."
            )
        else:
            pct_text = f", a {percent}% change" if percent else ""
            title = f"Material change: {label} (Fund {fund_number})"
            summary = (
                f"'{label}' in Fund {fund_number} {fund_name} changes from "
                f"{old_value} (FY 2025-26 actual) to {new_value} (FY 2026-27 "
                f"proposed budget){pct_text}. This change is above the configured "
                f"materiality threshold and needs explanation."
            )

        findings.append(
            Finding(
                finding_id=_finding_id("delta", fund_number, row["account"], label),
                title=title,
                category="delta",
                severity="medium" if row["status"] in ("new", "eliminated") else "low",
                confidence="low",
                summary=summary,
                evidence=[
                    f"document={row['document_id']}",
                    f"page={row['page_number']}",
                    f"account={row['account']}",
                    f"fund={fund_number} {fund_name}",
                ],
                open_questions=[
                    "What explains this change or presence/absence of this line item?",
                    "Is this recurring or one-time?",
                ],
                status="draft",
            )
        )

    return findings


def findings_from_compensation(compensation_flags_path: Path) -> list[Finding]:
    """Build one Finding per compensation line flagged 'needs_review' -- a
    label that plausibly identifies an individual position or is otherwise
    unclear, per docs/weakley-county.md 'Compensation visibility' questions.
    Rows classified 'aggregate' are expected category rollups and are not
    surfaced as findings.
    """
    rows = list(csv.DictReader(compensation_flags_path.open(encoding="utf-8")))
    findings: list[Finding] = []

    for row in rows:
        if row["classification"] != "needs_review":
            continue

        fund_number = row["fund_number"]
        fund_name = row["fund_name"] or FUND_NAMES.get(fund_number, fund_number)
        label = row["label"]

        findings.append(
            Finding(
                finding_id=_finding_id("comp", fund_number, row["account"], label),
                title=f"Compensation line needs explanation: {label} (Fund {fund_number})",
                category="salary",
                severity="info",
                confidence="low",
                summary=(
                    f"'{label}' in Fund {fund_number} {fund_name}, department "
                    f"'{row['department']}', is flagged by a coarse heuristic as "
                    f"possibly identifying an individual position rather than an "
                    f"aggregated category, at {row['budget_26_27'] or '(blank)'} "
                    f"for FY 2026-27. This classification is low-confidence and "
                    f"intended to prompt review, not to assert that any individual "
                    f"is identified."
                ),
                evidence=[
                    f"document={row['document_id']}",
                    f"page={row['page_number']}",
                    f"account={row['account']}",
                    f"fund={fund_number} {fund_name}",
                ],
                open_questions=[
                    "Does this line item represent one position or several?",
                    "Is a position title/department sufficient to identify who is compensated, or is more context needed?",
                ],
                status="draft",
            )
        )

    return findings


def findings_from_reconciliation(
    reconcile_paths: dict[str, Path],
    tolerance: int = 100,
) -> list[Finding]:
    """Build a Finding for any fund whose net_with_transfers is outside
    tolerance -- i.e. does not reconcile cleanly in this extraction.
    """
    findings: list[Finding] = []

    for fund_number, path in sorted(reconcile_paths.items()):
        reader = csv.reader(path.open(encoding="utf-8"))
        next(reader)  # header: "metric","value"
        metrics = {row[0]: row[1] for row in reader}
        net = int(metrics.get("net_with_transfers", "0"))
        fund_name = FUND_NAMES.get(fund_number, fund_number)

        if abs(net) > tolerance:
            findings.append(
                Finding(
                    finding_id=_finding_id("reconcile", fund_number),
                    title=f"Fund {fund_number} does not reconcile in this extraction",
                    category="reconciliation",
                    severity="low",
                    confidence="medium",
                    summary=(
                        f"Fund {fund_number} {fund_name} shows a net difference of "
                        f"{net} between revenue-with-transfers and "
                        f"expenditure-with-transfers in this OCR-derived extraction. "
                        f"This does not reconcile in this extraction; it may reflect "
                        f"an extraction error, an uncaptured line item, or a genuine "
                        f"source imbalance, and needs explanation."
                    ),
                    evidence=[f"reconciliation_file={path.name}", f"net_with_transfers={net}"],
                    open_questions=[
                        "Does the source document itself balance, or does the county packet show the same gap?"
                    ],
                    status="draft",
                )
            )

    return findings


def write_findings(findings: list[Finding], out_path: Path) -> int:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "finding_id",
        "title",
        "category",
        "severity",
        "confidence",
        "summary",
        "evidence",
        "open_questions",
        "status",
    ]
    with out_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for finding in findings:
            writer.writerow(
                {
                    "finding_id": finding.finding_id,
                    "title": finding.title,
                    "category": finding.category,
                    "severity": finding.severity,
                    "confidence": finding.confidence,
                    "summary": finding.summary,
                    "evidence": "; ".join(finding.evidence),
                    "open_questions": "; ".join(finding.open_questions),
                    "status": finding.status,
                }
            )
    return len(findings)


def build_findings(
    delta_rows_path: Path,
    compensation_flags_path: Path,
    reconcile_paths: dict[str, Path],
    out_path: Path,
) -> dict[str, int]:
    """Assemble delta, compensation, and reconciliation findings into one findings CSV."""
    delta_findings = findings_from_deltas(delta_rows_path)
    comp_findings = findings_from_compensation(compensation_flags_path)
    reconcile_findings = findings_from_reconciliation(reconcile_paths)

    all_findings = delta_findings + comp_findings + reconcile_findings
    write_findings(all_findings, out_path)

    return {
        "delta_findings": len(delta_findings),
        "compensation_findings": len(comp_findings),
        "reconciliation_findings": len(reconcile_findings),
        "total_findings": len(all_findings),
    }
