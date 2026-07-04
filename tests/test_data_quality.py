import csv
from decimal import Decimal
from pathlib import Path

from budget_audit.data_quality import (
    HIGH_IMPACT_THRESHOLD,
    ImpactContext,
    DataQualityWarning,
    analyze_data_quality,
    data_quality_impact_score,
    data_quality_warnings_for_row,
    is_high_impact,
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


def test_data_quality_warnings_for_row_populates_structured_fields() -> None:
    row = base_row()
    row["budget_26_27"] = "4O0"

    warnings = data_quality_warnings_for_row(row)

    assert warnings[0].document_id == "doc"
    assert warnings[0].page_number == "23"
    assert warnings[0].fund_number == "101"
    assert warnings[0].account == "40110"
    # budget_26_27 itself is unparseable, so amount falls back to actual_25_26.
    assert warnings[0].amount == Decimal("300")


def test_impact_score_high_severity_alone_clears_threshold() -> None:
    warning = DataQualityWarning(
        warning_id="dq-1",
        warning_type="unparsed_amount",
        severity="high",
        confidence="high",
        summary="x",
        evidence=[],
    )

    score = data_quality_impact_score(warning)

    assert is_high_impact(score)


def test_impact_score_low_severity_placeholder_stays_low_impact() -> None:
    warning = DataQualityWarning(
        warning_id="dq-2",
        warning_type="placeholder_amount",
        severity="low",
        confidence="medium",
        summary="x",
        evidence=[],
        amount=Decimal("1"),
    )

    score = data_quality_impact_score(warning)

    assert not is_high_impact(score)


def test_impact_score_rises_with_top_change_and_priority_cluster_context() -> None:
    warning = DataQualityWarning(
        warning_id="dq-3",
        warning_type="ocr_artifact_text",
        severity="medium",
        confidence="medium",
        summary="x",
        evidence=[],
        document_id="doc",
        page_number="23",
        fund_number="151",
        account="602",
    )

    bare_score = data_quality_impact_score(warning)
    context = ImpactContext(
        top_change_keys=frozenset({("doc", "23", "602")}),
        priority_fund_numbers=frozenset({"151"}),
    )
    contextual_score = data_quality_impact_score(warning, context)

    assert contextual_score > bare_score
    assert not is_high_impact(bare_score)
    assert is_high_impact(contextual_score)
    assert contextual_score >= HIGH_IMPACT_THRESHOLD


def test_analyze_data_quality_reports_high_impact_count(tmp_path: Path) -> None:
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

    assert stats["high_impact_warnings"] == 1

    rows = list(csv.DictReader(out_path.open(encoding="utf-8")))
    assert int(rows[0]["impact_score"]) >= HIGH_IMPACT_THRESHOLD
