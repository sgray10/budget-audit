from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from budget_audit.analyze import MaterialityThreshold, analyze_deltas
from budget_audit.clusters import build_clusters
from budget_audit.compensation import analyze_compensation
from budget_audit.consolidate import consolidate_reviewed_rows
from budget_audit.data_quality import (
    ImpactContext,
    compute_warnings,
    data_quality_impact_score,
    is_high_impact,
    write_data_quality_warnings,
)
from budget_audit.findings import build_findings
from budget_audit.json_export import csv_to_json, write_json
from budget_audit.manual_corrections import summarize_manual_corrections, write_manual_corrections
from budget_audit.priority_areas import build_priority_areas, write_priority_areas
from budget_audit.questions import PUBLIC_RECORDS_QUESTIONS
from budget_audit.report import load_reconcile_summary, render_report
from budget_audit.structural_changes import detect_grant_funded_capital_pairs, detect_whole_fund_changes
from budget_audit.top_changes import analyze_top_changes

# Cluster types priority_areas.py treats as notable -- used here only to
# decide which funds count as "belonging to a priority cluster" for
# data-quality impact scoring context, so this list has to match
# priority_areas.NOTABLE_CLUSTER_TYPES. Kept as a separate constant (not
# imported) to avoid a workflow-layer module depending on a naming detail
# internal to priority_areas' own ranking logic.
NOTABLE_CLUSTER_TYPES_FOR_DQ_CONTEXT = {
    "grant_funded_capital_project",
    "grant_funded_program",
    "allocation_program",
    "debt_service",
}


@dataclass(frozen=True)
class ReportWorkflowPaths:
    consolidated_rows: Path
    line_item_deltas: Path
    delta_summary_by_fund: Path
    compensation_rollup: Path
    compensation_flags: Path
    data_quality_warnings: Path
    top_changes: Path
    clusters: Path
    findings: Path
    manual_corrections: Path
    priority_areas: Path
    report_md: Path


def report_workflow_paths(out_dir: Path, reports_dir: Path, report_filename: str) -> ReportWorkflowPaths:
    return ReportWorkflowPaths(
        consolidated_rows=out_dir / "reviewed_funds_rows.csv",
        line_item_deltas=out_dir / "line_item_deltas.csv",
        delta_summary_by_fund=out_dir / "delta_summary_by_fund.csv",
        compensation_rollup=out_dir / "compensation_rollup.csv",
        compensation_flags=out_dir / "compensation_flags.csv",
        data_quality_warnings=out_dir / "data_quality_warnings.csv",
        top_changes=out_dir / "top_changes.csv",
        clusters=out_dir / "clusters.csv",
        findings=out_dir / "findings.csv",
        manual_corrections=out_dir / "manual_corrections.csv",
        priority_areas=out_dir / "priority_areas.csv",
        report_md=reports_dir / report_filename,
    )


def run_report_workflow(
    input_row_paths: list[Path],
    reconcile_paths: dict[str, Path],
    out_dir: Path,
    reports_dir: Path,
    report_filename: str,
    threshold: MaterialityThreshold = MaterialityThreshold(),
    verbosity: str = "standard",
) -> dict[str, int]:
    """Run the full pipeline: consolidate -> analyze-deltas ->
    analyze-compensation -> build-clusters -> analyze-top-changes ->
    detect structural/grant-capital signals -> build-findings ->
    analyze-data-quality (impact-scored against the above) ->
    summarize-manual-corrections -> build-priority-areas -> render report.

    Order matters here: clusters, top-changes, and findings are all
    computed before data-quality scoring, because impact scoring needs to
    know whether a warning's row shows up in a top-dollar change or a
    priority-typed cluster. Structural changes and grant/capital pairs only
    need line_item_deltas.csv, so they can run any time after analyze-deltas.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = report_workflow_paths(out_dir, reports_dir, report_filename)

    consolidated_count = consolidate_reviewed_rows(input_row_paths, paths.consolidated_rows)
    delta_stats = analyze_deltas(paths.consolidated_rows, out_dir, threshold)
    comp_stats = analyze_compensation(paths.consolidated_rows, out_dir)
    cluster_stats = build_clusters(paths.consolidated_rows, paths.clusters)
    top_change_stats = analyze_top_changes(paths.line_item_deltas, paths.top_changes)

    whole_fund_changes = detect_whole_fund_changes(paths.line_item_deltas)
    grant_capital_pairs = detect_grant_funded_capital_pairs(paths.line_item_deltas)

    finding_stats = build_findings(
        paths.line_item_deltas,
        paths.compensation_flags,
        reconcile_paths,
        paths.findings,
        whole_fund_changes=whole_fund_changes,
        grant_capital_pairs=grant_capital_pairs,
    )

    top_change_rows = list(csv.DictReader(paths.top_changes.open(encoding="utf-8")))
    top_change_keys = frozenset(
        (row.get("document_id", ""), row.get("page_number", ""), row.get("account", "")) for row in top_change_rows
    )
    cluster_rows = list(csv.DictReader(paths.clusters.open(encoding="utf-8")))
    priority_fund_numbers = frozenset(
        row["fund_number"] for row in cluster_rows if row["cluster_type"] in NOTABLE_CLUSTER_TYPES_FOR_DQ_CONTEXT
    )
    dq_context = ImpactContext(top_change_keys=top_change_keys, priority_fund_numbers=priority_fund_numbers)

    warnings = compute_warnings(paths.consolidated_rows)
    write_data_quality_warnings(warnings, paths.data_quality_warnings, dq_context)
    high_impact_warnings = [w for w in warnings if is_high_impact(data_quality_impact_score(w, dq_context))]

    manual_corrections_summary = summarize_manual_corrections(paths.consolidated_rows)
    write_manual_corrections(paths.consolidated_rows, paths.manual_corrections)

    manual_correction_funds = set(manual_corrections_summary.by_fund.keys())
    priority_areas = build_priority_areas(
        paths.clusters,
        whole_fund_changes,
        grant_capital_pairs,
        high_impact_warnings,
        manual_correction_funds,
    )
    write_priority_areas(priority_areas, paths.priority_areas)

    summaries = [load_reconcile_summary(fund, path) for fund, path in sorted(reconcile_paths.items())]
    render_report(
        paths.findings,
        summaries,
        paths.report_md,
        data_quality_path=paths.data_quality_warnings,
        top_changes_path=paths.top_changes,
        clusters_path=paths.clusters,
        priority_areas_path=paths.priority_areas,
        manual_corrections_summary=manual_corrections_summary,
        manual_corrections_path=paths.manual_corrections,
        verbosity=verbosity,
    )

    # Machine-readable siblings for the structured CSV outputs.
    csv_to_json(paths.findings, out_dir / "findings.json")
    csv_to_json(paths.clusters, out_dir / "clusters.json")
    csv_to_json(paths.data_quality_warnings, out_dir / "data_quality_warnings.json")
    csv_to_json(paths.manual_corrections, out_dir / "manual_corrections.json")
    csv_to_json(paths.priority_areas, out_dir / "priority_areas.json")
    write_json(PUBLIC_RECORDS_QUESTIONS, out_dir / "questions.json")
    write_json(summaries, out_dir / "reconciliation.json")

    return {
        "consolidated_rows": consolidated_count,
        "material_rows": delta_stats["material_rows"],
        "new_line_rows": delta_stats["new_line_rows"],
        "eliminated_line_rows": delta_stats["eliminated_line_rows"],
        "compensation_needs_review": comp_stats["needs_review_rows"],
        "data_quality_warnings": len(warnings),
        "high_impact_data_quality_warnings": len(high_impact_warnings),
        "top_change_rows": top_change_stats["top_change_rows"],
        "clusters": cluster_stats["clusters"],
        "paired_clusters": cluster_stats["paired_clusters"],
        "whole_fund_structural_changes": len(whole_fund_changes),
        "grant_capital_pairs": len(grant_capital_pairs),
        "manual_corrections": manual_corrections_summary.total,
        "priority_areas": len(priority_areas),
        "total_findings": finding_stats["total_findings"],
    }
