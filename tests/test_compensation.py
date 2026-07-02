import csv
from pathlib import Path

from budget_audit.compensation import analyze_compensation, classify_compensation_label

ROW_HEADER = (
    "document_id,page_number,category,contains_salary_or_compensation,fund_number,fund_name,"
    "department,division,account,label,budget_26_27\n"
)


def test_classify_compensation_label_aggregate() -> None:
    assert classify_compensation_label("Social Security", 45000) == "aggregate"
    assert classify_compensation_label("Medical Insurance", 120000) == "aggregate"
    assert classify_compensation_label("State Retirement", 30000) == "aggregate"
    assert classify_compensation_label("DGA Other Salaries & Wages", 15000) == "aggregate"
    assert classify_compensation_label("+ISM State Retirement", 8000) == "aggregate"
    assert classify_compensation_label("=ITG Social Security", 8000) == "aggregate"


def test_classify_compensation_label_needs_review() -> None:
    assert classify_compensation_label("Registrar's Salary Supplement", 4200) == "needs_review"
    assert classify_compensation_label("SAL Juvenile Services Salary", 51000) == "needs_review"
    # small unnamed dollar amount is plausibly a single-person line
    assert classify_compensation_label("Miscellaneous Stipend", 500) == "needs_review"


def test_analyze_compensation_rollup_and_flags(tmp_path: Path) -> None:
    rows_path = tmp_path / "rows.csv"
    out_dir = tmp_path / "out"

    rows_path.write_text(
        ROW_HEADER
        + "doc,23,compensation,true,101,General,Sheriff,,50100,Social Security,\"5,000\"\n"
        + "doc,23,compensation,true,101,General,Sheriff,,50101,Registrar's Salary Supplement,\"3,500\"\n"
        + "doc,23,operating,false,101,General,Sheriff,,50102,Supplies,\"1,000\"\n",
        encoding="utf-8",
    )

    stats = analyze_compensation(rows_path, out_dir)

    assert stats["compensation_rows"] == 2
    assert stats["needs_review_rows"] == 1
    assert stats["aggregate_rows"] == 1

    rollup_rows = list(csv.DictReader((out_dir / "compensation_rollup.csv").open(encoding="utf-8")))
    assert len(rollup_rows) == 1
    assert rollup_rows[0]["department"] == "Sheriff"
    assert rollup_rows[0]["budget_26_27_total"] == "8500"

    flag_rows = list(csv.DictReader((out_dir / "compensation_flags.csv").open(encoding="utf-8")))
    classifications = {row["label"]: row["classification"] for row in flag_rows}
    assert classifications["Social Security"] == "aggregate"
    assert classifications["Registrar's Salary Supplement"] == "needs_review"
