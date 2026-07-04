from pathlib import Path

from budget_audit.analyze import MaterialityThreshold
from budget_audit.report_workflow import report_workflow_paths, run_report_workflow

ROW_HEADER = (
    "document_id,page_number,row_type,category,contains_salary_or_compensation,fund_number,fund_name,"
    "section_hint,division,department,account,label,actual_24_25,budget_25_26,actual_25_26,budget_26_27\n"
)


def test_report_workflow_paths(tmp_path: Path) -> None:
    out_dir = tmp_path / "processed"
    reports_dir = tmp_path / "reports"

    paths = report_workflow_paths(out_dir, reports_dir, "weakley-fwm-2026-06-30.md")

    assert paths.consolidated_rows == out_dir / "reviewed_funds_rows.csv"
    assert paths.line_item_deltas == out_dir / "line_item_deltas.csv"
    assert paths.delta_summary_by_fund == out_dir / "delta_summary_by_fund.csv"
    assert paths.compensation_rollup == out_dir / "compensation_rollup.csv"
    assert paths.compensation_flags == out_dir / "compensation_flags.csv"
    assert paths.data_quality_warnings == out_dir / "data_quality_warnings.csv"
    assert paths.top_changes == out_dir / "top_changes.csv"
    assert paths.findings == out_dir / "findings.csv"
    assert paths.report_md == reports_dir / "weakley-fwm-2026-06-30.md"


def test_run_report_workflow_end_to_end(tmp_path: Path) -> None:
    first_range = tmp_path / "range_101.csv"
    first_range.write_text(
        ROW_HEADER
        + "doc,23,line_item,operating,false,101,General,Fund 101 General Fund expenditures,,,40110,Big Increase,,,\"10,000\",\"20,000\"\n"
        + "doc,23,line_item,compensation,true,101,General,Fund 101 General Fund expenditures,,Sheriff,40111,Registrar's Salary Supplement,,,\"3,000\",\"3,500\"\n",
        encoding="utf-8",
    )
    second_range = tmp_path / "range_141.csv"
    second_range.write_text(
        ROW_HEADER
        + "doc,90,line_item,operating,false,141,General Purpose School,Fund 141 General Purpose School expenditures,,,60110,Textbooks,,,\"1,000\",\"1,010\"\n",
        encoding="utf-8",
    )

    reconcile_101 = tmp_path / "reconcile_101.csv"
    reconcile_101.write_text(
        "metric,value\nrevenue_with_transfers,0\nexpenditure_with_transfers,25000\nnet_with_transfers,-25000\n",
        encoding="utf-8",
    )
    reconcile_141 = tmp_path / "reconcile_141.csv"
    reconcile_141.write_text(
        "metric,value\nrevenue_with_transfers,1010\nexpenditure_with_transfers,1010\nnet_with_transfers,0\n",
        encoding="utf-8",
    )

    out_dir = tmp_path / "processed"
    reports_dir = tmp_path / "reports"

    stats = run_report_workflow(
        [first_range, second_range],
        {"101": reconcile_101, "141": reconcile_141},
        out_dir,
        reports_dir,
        "test-report.md",
        MaterialityThreshold(),
    )

    assert stats["consolidated_rows"] == 3
    # Big Increase clears both the absolute ($10,000) and percent (100%) thresholds.
    # Registrar's Salary Supplement clears percent (16.7%) but not the $5,000
    # absolute floor, so it is not material under the require-both default --
    # it still surfaces separately as a compensation needs_review finding.
    assert stats["material_rows"] == 1
    assert stats["compensation_needs_review"] == 1  # Registrar's Salary Supplement
    assert stats["data_quality_warnings"] == 0
    assert stats["top_change_rows"] > 0
    assert stats["total_findings"] >= 3  # delta + compensation + reconciliation (fund 101 out of tolerance)

    report_path = reports_dir / "test-report.md"
    assert report_path.exists()
    content = report_path.read_text(encoding="utf-8")
    assert "Fund 101 does not reconcile" in content
    assert "## Data-quality warnings" in content
    assert "## Top changes" in content
    assert "| 141 | General Purpose School |" in content
