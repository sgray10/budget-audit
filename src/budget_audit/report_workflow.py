from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from budget_audit.analyze import MaterialityThreshold, analyze_deltas
from budget_audit.compensation import analyze_compensation
from budget_audit.consolidate import consolidate_reviewed_rows
from budget_audit.data_quality import analyze_data_quality
from budget_audit.findings import build_findings
from budget_audit.report import load_reconcile_summary, render_report


@dataclass(frozen=True)
class ReportWorkflowPaths:
    consolidated_rows: Path
    line_item_deltas: Path
    delta_summary_by_fund: Path
    compensation_rollup: Path
    compensation_flags: Path
    data_quality_warnings: Path
    findings: Path
    report_md: Path


def report_workflow_paths(out_dir: Path, reports_dir: Path, report_filename: str) -> ReportWorkflowPaths:
    return ReportWorkflowPaths(
        consolidated_rows=out_dir / "reviewed_funds_rows.csv",
        line_item_deltas=out_dir / "line_item_deltas.csv",
        delta_summary_by_fund=out_dir / "delta_summary_by_fund.csv",
        compensation_rollup=out_dir / "compensation_rollup.csv",
        compensation_flags=out_dir / "compensation_flags.csv",
        data_quality_warnings=out_dir / "data_quality_warnings.csv",
        findings=out_dir / "findings.csv",
        report_md=reports_dir / report_filename,
    )


def run_report_workflow(
    input_row_paths: list[Path],
    reconcile_paths: dict[str, Path],
    out_dir: Path,
    reports_dir: Path,
    report_filename: str,
    threshold: MaterialityThreshold = MaterialityThreshold(),
) -> dict[str, int]:
    """Run consolidate -> analyze-deltas -> analyze-compensation ->
    build-findings -> report end to end for the reviewed/corrected row files.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = report_workflow_paths(out_dir, reports_dir, report_filename)

    consolidated_count = consolidate_reviewed_rows(input_row_paths, paths.consolidated_rows)
    delta_stats = analyze_deltas(paths.consolidated_rows, out_dir, threshold)
    comp_stats = analyze_compensation(paths.consolidated_rows, out_dir)
    data_quality_stats = analyze_data_quality(paths.consolidated_rows, paths.data_quality_warnings)
    finding_stats = build_findings(
        paths.line_item_deltas, paths.compensation_flags, reconcile_paths, paths.findings
    )

    summaries = [
        load_reconcile_summary(fund, path) for fund, path in sorted(reconcile_paths.items())
    ]
    render_report(paths.findings, summaries, paths.report_md, data_quality_path=paths.data_quality_warnings)

    return {
        "consolidated_rows": consolidated_count,
        "material_rows": delta_stats["material_rows"],
        "new_line_rows": delta_stats["new_line_rows"],
        "eliminated_line_rows": delta_stats["eliminated_line_rows"],
        "compensation_needs_review": comp_stats["needs_review_rows"],
        "data_quality_warnings": data_quality_stats["data_quality_warnings"],
        "total_findings": finding_stats["total_findings"],
    }
