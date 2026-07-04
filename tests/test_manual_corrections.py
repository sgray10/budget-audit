import csv
from pathlib import Path

from budget_audit.manual_corrections import (
    manual_correction_rows,
    summarize_manual_corrections,
    write_manual_corrections,
)

ROWS_HEADER = (
    "document_id,page_number,fund_number,fund_name,account,label,budget_26_27,correction_action,"
    "correction_reason\n"
)


def test_manual_correction_rows_filters_to_corrected_only(tmp_path: Path) -> None:
    rows_path = tmp_path / "rows.csv"
    rows_path.write_text(
        ROWS_HEADER
        + "doc,23,101,General,40110,Corrected Row,5000,add,extraction gap\n"
        + "doc,24,101,General,40111,Untouched Row,3000,,\n",
        encoding="utf-8",
    )

    corrected = manual_correction_rows(rows_path)

    assert len(corrected) == 1
    assert corrected[0]["label"] == "Corrected Row"


def test_summarize_manual_corrections_counts_by_fund_and_action(tmp_path: Path) -> None:
    rows_path = tmp_path / "rows.csv"
    rows_path.write_text(
        ROWS_HEADER
        + "doc,23,101,General,40110,Row One,5000,add,reason one\n"
        + "doc,24,101,General,40111,Row Two,3000,replace,reason two\n"
        + "doc,90,141,General Purpose School,60110,Row Three,2000,add,reason three\n",
        encoding="utf-8",
    )

    summary = summarize_manual_corrections(rows_path)

    assert summary.total == 3
    assert summary.by_fund == {"101": 2, "141": 1}
    assert summary.by_action == {"add": 2, "replace": 1}


def test_summarize_manual_corrections_ranks_high_impact_by_dollar_amount(tmp_path: Path) -> None:
    rows_path = tmp_path / "rows.csv"
    rows_path.write_text(
        ROWS_HEADER
        + "doc,23,101,General,40110,Big Correction,1579857,add,large addition\n"
        + "doc,24,101,General,40111,Small Correction,50,add,balancing correction\n",
        encoding="utf-8",
    )

    summary = summarize_manual_corrections(rows_path)

    assert len(summary.high_impact) == 1
    assert summary.high_impact[0]["label"] == "Big Correction"


def test_write_manual_corrections_round_trip(tmp_path: Path) -> None:
    rows_path = tmp_path / "rows.csv"
    rows_path.write_text(
        ROWS_HEADER + "doc,23,101,General,40110,Row One,5000,add,reason one\n",
        encoding="utf-8",
    )
    out_path = tmp_path / "manual_corrections.csv"

    count = write_manual_corrections(rows_path, out_path)

    assert count == 1
    rows = list(csv.DictReader(out_path.open(encoding="utf-8")))
    assert rows[0]["label"] == "Row One"
    assert rows[0]["correction_action"] == "add"
