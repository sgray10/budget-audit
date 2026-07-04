from __future__ import annotations

import csv
from pathlib import Path

from budget_audit.classify import categorize_line_item
from budget_audit.clusters import cluster_id_for, extract_label_prefix
from budget_audit.models import Finding
from budget_audit.questions import questions_for_category
from budget_audit.structural_changes import GrantFundedCapitalPair, WholeFundChange

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

MANUAL_CORRECTION_DEPENDENCY_NOTE = (
    "This finding depends on a traceable manual correction; verify correction metadata before relying on it."
)


def _finding_id(prefix: str, *parts: str) -> str:
    slug = "-".join(part.strip().lower().replace(" ", "-").replace("/", "-") for part in parts if part)
    return f"{prefix}-{slug}"[:120]


def _cluster_id(fund_number: str, label: str) -> str | None:
    prefix = extract_label_prefix(label)
    return cluster_id_for(fund_number, prefix) if prefix else None


def findings_from_deltas(delta_rows_path: Path) -> list[Finding]:
    """Build one Finding per material, new, or eliminated line item on the
    headline actual_25_26 -> budget_26_27 transition. Non-headline transitions
    are analytical detail (see line_item_deltas.csv), not surfaced here, so a
    single line item does not produce up to four duplicate findings.

    Category is assigned by classify.categorize_line_item() -- account
    number first, label as fallback -- so a line like "Building & Contents
    Insurance" (account 502) lands in insurance_or_claims, not
    capital_project, regardless of the word "Building".
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
        category = categorize_line_item(row.get("account", ""), label, row.get("budget_side", ""))

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

        if row.get("correction_action", ""):
            summary = f"{summary} {MANUAL_CORRECTION_DEPENDENCY_NOTE}"

        findings.append(
            Finding(
                finding_id=_finding_id("delta", fund_number, row["account"], label),
                title=title,
                category=category,
                severity="medium" if row["status"] in ("new", "eliminated") else "low",
                confidence="low",
                summary=summary,
                evidence=[
                    f"document={row['document_id']}",
                    f"page={row['page_number']}",
                    f"account={row['account']}",
                    f"fund={fund_number} {fund_name}",
                ],
                open_questions=questions_for_category(category),
                cluster_id=_cluster_id(fund_number, label),
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
                category="personnel",
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
                open_questions=questions_for_category("personnel"),
                cluster_id=_cluster_id(fund_number, label),
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
                    open_questions=questions_for_category("reconciliation"),
                )
            )

    return findings


def findings_from_structural_changes(changes: list[WholeFundChange]) -> list[Finding]:
    """Build a Finding for each whole-fund structural change (revenue and
    expenditure both collapsing to ~zero, or the reverse) -- a fund-level
    pattern distinct from any single line item. See structural_changes.py.
    """
    findings: list[Finding] = []
    for change in changes:
        direction_text = (
            "both drop from materially active levels to near zero"
            if change.direction == "zeroed_out"
            else "both appear from near zero to materially active levels"
        )
        findings.append(
            Finding(
                finding_id=_finding_id("structural", change.fund_number),
                title=f"Fund {change.fund_number} {change.fund_name}: fund-wide revenue and expenditure change",
                category="whole_fund_structural_change",
                severity="medium",
                confidence="medium",
                summary=(
                    f"Fund {change.fund_number} {change.fund_name}'s revenue and expenditure {direction_text} "
                    f"in the proposed budget (revenue {change.revenue_old} -> {change.revenue_new}; "
                    f"expenditure {change.expenditure_old} -> {change.expenditure_new}). This is a "
                    f"fund-wide pattern, not an isolated line item, and needs explanation."
                ),
                evidence=[f"fund={change.fund_number} {change.fund_name}"]
                + [f"sample_label={label}" for label in change.sample_labels],
                open_questions=questions_for_category("whole_fund_structural_change"),
            )
        )
    return findings


def findings_from_grant_capital_pairs(pairs: list[GrantFundedCapitalPair]) -> list[Finding]:
    """Build a Finding for each fund-level grant-revenue/capital-expense
    pairing of comparable magnitude, even when the two labels share no
    common prefix (see structural_changes.detect_grant_funded_capital_pairs).
    """
    findings: list[Finding] = []
    for pair in pairs:
        findings.append(
            Finding(
                finding_id=_finding_id("grant-capital", pair.fund_number),
                title=f"Fund {pair.fund_number} {pair.fund_name}: paired grant revenue and capital expense",
                category="grant_funded_capital_project",
                severity="low",
                confidence="low",
                summary=(
                    f"Fund {pair.fund_number} {pair.fund_name} shows '{pair.revenue_label}' revenue "
                    f"increasing by {pair.revenue_delta} alongside '{pair.expenditure_label}' expense "
                    f"increasing by {pair.expenditure_delta} -- comparable magnitude, suggesting a single "
                    f"grant-funded capital project rather than two unrelated changes."
                ),
                evidence=[
                    f"fund={pair.fund_number} {pair.fund_name}",
                    f"revenue_label={pair.revenue_label}",
                    f"expenditure_label={pair.expenditure_label}",
                ],
                open_questions=questions_for_category("grant_funded_capital_project"),
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
        "cluster_id",
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
                    "cluster_id": finding.cluster_id or "",
                }
            )
    return len(findings)


def build_findings(
    delta_rows_path: Path,
    compensation_flags_path: Path,
    reconcile_paths: dict[str, Path],
    out_path: Path,
    whole_fund_changes: list[WholeFundChange] | None = None,
    grant_capital_pairs: list[GrantFundedCapitalPair] | None = None,
) -> dict[str, int]:
    """Assemble delta, compensation, reconciliation, structural-change, and
    grant/capital-pair findings into one findings CSV.
    """
    delta_findings = findings_from_deltas(delta_rows_path)
    comp_findings = findings_from_compensation(compensation_flags_path)
    reconcile_findings = findings_from_reconciliation(reconcile_paths)
    structural_findings = findings_from_structural_changes(whole_fund_changes or [])
    grant_capital_findings = findings_from_grant_capital_pairs(grant_capital_pairs or [])

    all_findings = (
        delta_findings + comp_findings + reconcile_findings + structural_findings + grant_capital_findings
    )
    write_findings(all_findings, out_path)

    return {
        "delta_findings": len(delta_findings),
        "compensation_findings": len(comp_findings),
        "reconciliation_findings": len(reconcile_findings),
        "structural_change_findings": len(structural_findings),
        "grant_capital_pair_findings": len(grant_capital_findings),
        "total_findings": len(all_findings),
    }

