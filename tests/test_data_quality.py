import csv
from pathlib import Path

from budget_audit.data_quality import (
    analyze_data_quality,
    data_quality_warnings_for_row,
)


def base_row() -> dict[str, str]:
    return {
        "document_id": "doc",
        "page_number": "23",
        "row_type": "line_item",
        "fund_number": "101",
        "fund_name": "General",
        "section_hint": "Fund 101 General Fund expenditures",
        "account": "40110",
        "label": "Office Supplies",
        "actual_24_25": "100",
        "budget_25_26": "200",
        "actual_25_26": "300",
        "budget_26_27": "400",
        "raw_line": "40110 Office Supplies 100 200 300 400",
    }


def test_data_quality_warnings_for_clean_row() -> None:
    assert data_quality_warnings_for_row(base_row()) == []


def test_data_quality_warnings_flags_unparsed_amount() -> None:
    row = base_row()
    row["budget_26_27"] = "4O0"

    warnings = data_quality_warnings_for_row(row)

    assert [warning.warning_type for warning in warnings] == ["unparsed_amount"]
    assert warnings[0].severity == "high"
    assert "budget_26_27=4O0" in warnings[0].evidence


def test_data_quality_warnings_flags_placeholder_amount() -> None:
    row = base_row()
    row["actual_25_26"] = "1"

    warnings = data_quality_warnings_for_row(row)

    assert [warning.warning_type for warning in warnings] == ["placeholder_amount"]


def test_data_quality_warnings_flags_ocr_artifact_text() -> None:
    row = base_row()
    row["label"] = "Office §upplies"

    warnings = data_quality_warnings_for_row(row)

    assert [warning.warning_type for warning in warnings] == ["ocr_artifact_text"]


def test_data_quality_warnings_flags_manual_correction() -> None:
    row = base_row()
    row["correction_action"] = "replace"

    warnings = data_quality_warnings_for_row(row)

    assert [warning.warning_type for warning in warnings] == ["manual_correction"]
    assert warnings[0].severity == "info"


def test_analyze_data_quality_writes_structured_warnings(tmp_path: Path) -> None:
    rows_path = tmp_path / "rows.csv"
    out_path = tmp_path / "data_quality.csv"
    rows_path.write_text(
        "document_id,page_number,row_type,fund_number,fund_name,section_hint,account,label,"
        "actual_24_25,budget_25_26,actual_25_26,budget_26_27,raw_line\n"
        "doc,23,line_item,101,General,Fund 101 General Fund expenditures,40110,"
        "Office Supplies,100,200,300,4O0,raw\n",
        encoding="utf-8",
    )

    stats = analyze_data_quality(rows_path, out_path)

    assert stats["data_quality_warnings"] == 1
    assert stats["high_severity_warnings"] == 1

    rows = list(csv.DictReader(out_path.open(encoding="utf-8")))
    assert rows[0]["warning_type"] == "unparsed_amount"
    assert rows[0]["status"] == "needs_manual_verification"
