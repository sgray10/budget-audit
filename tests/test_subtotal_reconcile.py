import csv
from pathlib import Path

from budget_audit.subtotal_reconcile import reconcile_subtotals

ROW_HEADER = "fund_number,page_number,line_number,row_type,label,budget_26_27,raw_line\n"


def test_single_page_group_matches(tmp_path: Path) -> None:
    rows_path = tmp_path / "rows.csv"
    out_path = tmp_path / "mismatches.csv"

    rows_path.write_text(
        ROW_HEADER
        + "101,23,1,line_item,Current Tax,100,raw1\n"
        + "101,23,2,line_item,Trustee Collection,50,raw2\n"
        + "101,23,3,total,Sub-Total,150,Sub-Total 150\n",
        encoding="utf-8",
    )

    stats = reconcile_subtotals(rows_path, out_path)

    assert stats["total_rows_seen"] == 1
    assert stats["compared"] == 1
    assert stats["matched"] == 1
    assert stats["mismatched"] == 0

    mismatches = list(csv.DictReader(out_path.open(encoding="utf-8")))
    assert mismatches == []


def test_single_page_group_mismatches(tmp_path: Path) -> None:
    rows_path = tmp_path / "rows.csv"
    out_path = tmp_path / "mismatches.csv"

    rows_path.write_text(
        ROW_HEADER
        + "101,23,1,line_item,Current Tax,100,raw1\n"
        + "101,23,2,line_item,Trustee Collection,50,raw2\n"
        + "101,23,3,total,Sub-Total,200,Sub-Total 200\n",
        encoding="utf-8",
    )

    stats = reconcile_subtotals(rows_path, out_path)

    assert stats["compared"] == 1
    assert stats["matched"] == 0
    assert stats["mismatched"] == 1

    mismatches = list(csv.DictReader(out_path.open(encoding="utf-8")))
    assert len(mismatches) == 1
    assert mismatches[0]["expected"] == "150"
    assert mismatches[0]["actual"] == "200"
    assert mismatches[0]["difference"] == "-50"
    assert mismatches[0]["line_item_count"] == "2"
    assert mismatches[0]["total_raw_line"] == "Sub-Total 200"


def test_continuation_page_group(tmp_path: Path) -> None:
    rows_path = tmp_path / "rows.csv"
    out_path = tmp_path / "mismatches.csv"

    # Line items span page 90 and page 91; the total only appears on page 91,
    # with no total row closing out page 90 in between.
    rows_path.write_text(
        ROW_HEADER
        + "141,90,12,line_item,Teachers,1000,raw1\n"
        + "141,90,13,line_item,Aides,500,raw2\n"
        + "141,91,1,line_item,Substitutes,250,raw3\n"
        + "141,91,2,total,Sub-Total,1750,Sub-Total 1750\n",
        encoding="utf-8",
    )

    stats = reconcile_subtotals(rows_path, out_path)

    assert stats["compared"] == 1
    assert stats["matched"] == 1

    mismatches = list(csv.DictReader(out_path.open(encoding="utf-8")))
    assert mismatches == []


def test_continuation_page_group_mismatch_reports_span(tmp_path: Path) -> None:
    rows_path = tmp_path / "rows.csv"
    out_path = tmp_path / "mismatches.csv"

    rows_path.write_text(
        ROW_HEADER
        + "141,90,12,line_item,Teachers,1000,raw1\n"
        + "141,91,1,line_item,Substitutes,250,raw3\n"
        + "141,91,2,total,Sub-Total,2000,Sub-Total 2000\n",
        encoding="utf-8",
    )

    reconcile_subtotals(rows_path, out_path)

    mismatches = list(csv.DictReader(out_path.open(encoding="utf-8")))
    assert len(mismatches) == 1
    assert mismatches[0]["start_page"] == "90"
    assert mismatches[0]["start_line"] == "12"
    assert mismatches[0]["end_page"] == "91"
    assert mismatches[0]["end_line"] == "1"


def test_zero_line_item_total_is_skipped(tmp_path: Path) -> None:
    rows_path = tmp_path / "rows.csv"
    out_path = tmp_path / "mismatches.csv"

    # "Total Expense" followed immediately by "Total Regular Instruction" --
    # a roll-up restatement with zero line items in between.
    rows_path.write_text(
        ROW_HEADER
        + "141,91,10,line_item,Teachers,1000,raw1\n"
        + "141,91,11,total,Total Expense,1000,Total Expense 1000\n"
        + "141,91,12,total,Total Regular Instruction,1000,Total Regular Instruction 1000\n",
        encoding="utf-8",
    )

    stats = reconcile_subtotals(rows_path, out_path)

    assert stats["total_rows_seen"] == 2
    assert stats["compared"] == 1
    assert stats["matched"] == 1
    assert stats["skipped_zero_line_item_groups"] == 1

    mismatches = list(csv.DictReader(out_path.open(encoding="utf-8")))
    assert mismatches == []


def test_total_row_unparsed_amount(tmp_path: Path) -> None:
    rows_path = tmp_path / "rows.csv"
    out_path = tmp_path / "mismatches.csv"

    rows_path.write_text(
        ROW_HEADER
        + "101,23,1,line_item,Current Tax,100,raw1\n"
        + "101,23,2,total,Sub-Total,not-a-number,Sub-Total garbled\n",
        encoding="utf-8",
    )

    stats = reconcile_subtotals(rows_path, out_path)

    assert stats["unparsed_total_amounts"] == 1
    assert stats["mismatched"] == 1

    mismatches = list(csv.DictReader(out_path.open(encoding="utf-8")))
    assert len(mismatches) == 1
    assert mismatches[0]["note"] == "total_amount_unparsed"
    assert mismatches[0]["actual"] == ""


def test_unparsed_line_item_lowers_confidence(tmp_path: Path) -> None:
    rows_path = tmp_path / "rows.csv"
    out_path = tmp_path / "mismatches.csv"

    rows_path.write_text(
        ROW_HEADER
        + "101,23,1,line_item,Current Tax,not-a-number,raw1\n"
        + "101,23,2,line_item,Trustee Collection,50,raw2\n"
        + "101,23,3,total,Sub-Total,200,Sub-Total 200\n",
        encoding="utf-8",
    )

    stats = reconcile_subtotals(rows_path, out_path)

    assert stats["mismatched"] == 1
    mismatches = list(csv.DictReader(out_path.open(encoding="utf-8")))
    assert mismatches[0]["confidence"] == "low"
    assert mismatches[0]["unparsed_line_items"] == "1"
    assert mismatches[0]["expected"] == "50"


def test_fund_boundary_resets_group(tmp_path: Path) -> None:
    rows_path = tmp_path / "rows.csv"
    out_path = tmp_path / "mismatches.csv"

    rows_path.write_text(
        ROW_HEADER
        + "101,23,1,line_item,Current Tax,100,raw1\n"
        + "116,24,1,total,Sub-Total,999,Sub-Total 999\n",
        encoding="utf-8",
    )

    stats = reconcile_subtotals(rows_path, out_path)

    # Fund 116's total row starts a fresh group (fund changed), so it sees
    # zero line items and is treated as a roll-up skip, not a mismatch
    # against fund 101's line item.
    assert stats["skipped_zero_line_item_groups"] == 1
    assert stats["compared"] == 0

    mismatches = list(csv.DictReader(out_path.open(encoding="utf-8")))
    assert mismatches == []
