import csv
from pathlib import Path

import pytest

from budget_audit.corrections import apply_row_corrections
from budget_audit.reconcile import reconcile_fund
from budget_audit.subtotal_reconcile import reconcile_subtotals

ROWS_HEADER = "document_id,page_number,account,label,budget_26_27,raw_line\n"
CORRECTIONS_HEADER = "document_id,page_number,action,account,label,budget_26_27,reason,raw_line\n"

# Full 26-column schema needed for the reconcile_fund/reconcile_subtotals
# integration tests below -- apply_row_corrections' add path sets several
# fields (category, review_confidence, contains_budget_table, etc.)
# unconditionally, so the extracted-rows fixture must have all of them.
FULL_ROWS_HEADER = (
    "document_id,page_number,line_number,context_hint,category,row_type,review_confidence,"
    "contains_salary_or_compensation,contains_budget_table,division,department,fund_name,"
    "fund_number,page_type,section_hint,account,label,actual_24_25,budget_25_26,"
    "actual_25_26,budget_26_27,parse_status,raw_line\n"
)
FULL_CORRECTIONS_HEADER = (
    "document_id,page_number,line_number,action,fund_number,section_hint,row_type,category,"
    "account,label,actual_24_25,budget_25_26,actual_25_26,budget_26_27,reason,raw_line\n"
)


def test_apply_row_corrections_replaces_and_adds(tmp_path: Path) -> None:
    rows_path = tmp_path / "rows.csv"
    corrections_path = tmp_path / "corrections.csv"
    out_path = tmp_path / "corrected.csv"

    rows_path.write_text(
        "document_id,page_number,line_number,context_hint,category,row_type,review_confidence,"
        "contains_salary_or_compensation,contains_budget_table,division,department,fund_name,"
        "fund_number,page_type,section_hint,account,label,actual_24_25,budget_25_26,"
        "actual_25_26,budget_26_27,parse_status,raw_line\n"
        "doc,1,10,,operating,line_item,high,false,true,,,Highway,131,budget_table,"
        "Fund 131 Highway revenues,40320,Bank Excise Tax,11800,11000,7777,41000,parsed,raw\n",
        encoding="utf-8",
    )

    corrections_path.write_text(
        "document_id,page_number,line_number,action,fund_number,section_hint,account,label,"
        "actual_24_25,budget_25_26,actual_25_26,budget_26_27,reason,raw_line\n"
        "doc,1,,replace,131,Fund 131 Highway revenues,40320,Bank Excise Tax,11800,11000,7777,11000,fix,raw corrected\n"
        "doc,2,20,add,131,Fund 131 Highway expenditures,210,Unemployment Compensation,4225,5000,0,5000,missing,raw add\n",
        encoding="utf-8",
    )

    stats = apply_row_corrections(rows_path, corrections_path, out_path)
    output = out_path.read_text(encoding="utf-8")

    assert stats == {
        "input_rows": 1,
        "output_rows": 2,
        "replaced": 1,
        "added": 1,
        "unmatched_replacements": [],
        "ambiguous_extracted_matches": [],
        "ambiguous_correction_keys": [],
    }
    assert "11000" in output
    assert "Unemployment Compensation" in output
    assert "manual_correction" in output


def test_unmatched_replacement_reported_non_strict(tmp_path: Path) -> None:
    rows_path = tmp_path / "rows.csv"
    corrections_path = tmp_path / "corrections.csv"
    out_path = tmp_path / "corrected.csv"

    rows_path.write_text(
        ROWS_HEADER + "doc,105,791,Some Other Line,100,raw\n",
        encoding="utf-8",
    )
    # Mirrors the real Fund 141 case: a replace targeting a row that was
    # never extracted (page 106 never appears in rows.csv).
    corrections_path.write_text(
        CORRECTIONS_HEADER
        + "doc,106,replace,790,Other Equipment,1,fix,raw corrected\n",
        encoding="utf-8",
    )

    stats = apply_row_corrections(rows_path, corrections_path, out_path)

    assert stats["replaced"] == 0
    assert len(stats["unmatched_replacements"]) == 1
    assert "page=106" in stats["unmatched_replacements"][0]
    assert "account=790" in stats["unmatched_replacements"][0]
    output = out_path.read_text(encoding="utf-8")
    assert "Some Other Line" in output
    assert "100" in output


def test_unmatched_replacement_raises_in_strict_mode(tmp_path: Path) -> None:
    rows_path = tmp_path / "rows.csv"
    corrections_path = tmp_path / "corrections.csv"
    out_path = tmp_path / "corrected.csv"

    rows_path.write_text(ROWS_HEADER + "doc,105,791,Some Other Line,100,raw\n", encoding="utf-8")
    corrections_path.write_text(
        CORRECTIONS_HEADER + "doc,106,replace,790,Other Equipment,1,fix,raw corrected\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="unmatched"):
        apply_row_corrections(rows_path, corrections_path, out_path, strict=True)


def test_ambiguous_extracted_rows_not_modified(tmp_path: Path) -> None:
    rows_path = tmp_path / "rows.csv"
    corrections_path = tmp_path / "corrections.csv"
    out_path = tmp_path / "corrected.csv"

    # Two extracted rows share the same (document_id, page_number, account, label) key.
    rows_path.write_text(
        ROWS_HEADER
        + "doc,1,100,Supplies,50,raw1\n"
        + "doc,1,100,Supplies,999,raw2\n",
        encoding="utf-8",
    )
    corrections_path.write_text(
        CORRECTIONS_HEADER + "doc,1,replace,100,Supplies,75,fix,raw corrected\n",
        encoding="utf-8",
    )

    stats = apply_row_corrections(rows_path, corrections_path, out_path)

    assert stats["replaced"] == 0
    assert len(stats["ambiguous_extracted_matches"]) == 1
    output = out_path.read_text(encoding="utf-8")
    assert "50" in output
    assert "999" in output
    assert "75" not in output


def test_ambiguous_extracted_rows_raise_in_strict_mode(tmp_path: Path) -> None:
    rows_path = tmp_path / "rows.csv"
    corrections_path = tmp_path / "corrections.csv"
    out_path = tmp_path / "corrected.csv"

    rows_path.write_text(
        ROWS_HEADER + "doc,1,100,Supplies,50,raw1\n" + "doc,1,100,Supplies,999,raw2\n",
        encoding="utf-8",
    )
    corrections_path.write_text(
        CORRECTIONS_HEADER + "doc,1,replace,100,Supplies,75,fix,raw corrected\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="ambiguous"):
        apply_row_corrections(rows_path, corrections_path, out_path, strict=True)


def test_duplicate_correction_keys_last_one_wins_and_does_not_raise_in_strict(tmp_path: Path) -> None:
    rows_path = tmp_path / "rows.csv"
    corrections_path = tmp_path / "corrections.csv"
    out_path = tmp_path / "corrected.csv"

    rows_path.write_text(ROWS_HEADER + "doc,1,100,Supplies,50,raw\n", encoding="utf-8")
    # Two replace corrections targeting the same key -- current behavior
    # keeps the last one, and this is deliberately NOT a strict-mode failure.
    corrections_path.write_text(
        CORRECTIONS_HEADER
        + "doc,1,replace,100,Supplies,60,first fix,raw1\n"
        + "doc,1,replace,100,Supplies,70,second fix,raw2\n",
        encoding="utf-8",
    )

    stats = apply_row_corrections(rows_path, corrections_path, out_path, strict=True)

    assert stats["replaced"] == 1
    assert len(stats["ambiguous_correction_keys"]) == 1
    output = out_path.read_text(encoding="utf-8")
    assert "70" in output
    assert "60" not in output


def test_whitespace_tolerant_matching(tmp_path: Path) -> None:
    rows_path = tmp_path / "rows.csv"
    corrections_path = tmp_path / "corrections.csv"
    out_path = tmp_path / "corrected.csv"

    # Extracted label has an OCR-artifact double space; correction targets
    # the normalized (single-space) form.
    rows_path.write_text(
        ROWS_HEADER + 'doc,1,790,"Other  Equipment",1,raw\n',
        encoding="utf-8",
    )
    corrections_path.write_text(
        CORRECTIONS_HEADER + "doc,1,replace,790,Other Equipment,2,fix,raw corrected\n",
        encoding="utf-8",
    )

    stats = apply_row_corrections(rows_path, corrections_path, out_path)

    assert stats["replaced"] == 1
    assert stats["unmatched_replacements"] == []


def test_add_correction_defaults_row_type_and_category_when_unspecified(tmp_path: Path) -> None:
    rows_path = tmp_path / "rows.csv"
    corrections_path = tmp_path / "corrections.csv"
    out_path = tmp_path / "corrected.csv"

    rows_path.write_text(
        FULL_ROWS_HEADER
        + "doc,1,100,,operating,line_item,high,false,true,,,General,101,budget_table,"
        "Fund 101 General Fund expenditures,510,Supplies,,,,50,parsed,raw\n",
        encoding="utf-8",
    )
    # row_type/category left blank -- existing correction files (predating
    # issue #14) look like this and must keep working unchanged.
    corrections_path.write_text(
        FULL_CORRECTIONS_HEADER
        + "doc,1,101,add,101,Fund 101 General Fund expenditures,,,200,New Line,,,,5000,missing,raw add\n",
        encoding="utf-8",
    )

    apply_row_corrections(rows_path, corrections_path, out_path)

    rows = list(csv.DictReader(out_path.open(encoding="utf-8")))
    added = next(row for row in rows if row["label"] == "New Line")
    assert added["row_type"] == "line_item"
    assert added["category"] == "operating"


def test_add_correction_with_explicit_transfer_row_type_reconciles_correctly(tmp_path: Path) -> None:
    rows_path = tmp_path / "rows.csv"
    corrections_path = tmp_path / "corrections.csv"
    corrected_path = tmp_path / "corrected.csv"
    reconcile_path = tmp_path / "reconcile.csv"

    rows_path.write_text(
        FULL_ROWS_HEADER
        + "doc,1,10,,operating,line_item,high,false,true,,,General,101,budget_table,"
        "Fund 101 General Fund expenditures,510,Supplies,,,,1000,parsed,raw\n",
        encoding="utf-8",
    )
    # A "49800 Transfers In" row that failed extraction (mirrors the real
    # Fund 172 case), this time with a nonzero amount so mis-bucketing it as
    # a line_item instead of a transfer would actually change the numbers.
    corrections_path.write_text(
        FULL_CORRECTIONS_HEADER
        + "doc,1,11,add,101,Fund 101 General Fund revenues,transfer,transfer,49800,Transfers In,,,,5000,missing,raw add\n",
        encoding="utf-8",
    )

    apply_row_corrections(rows_path, corrections_path, corrected_path)

    added_rows = list(csv.DictReader(corrected_path.open(encoding="utf-8")))
    added = next(row for row in added_rows if row["label"] == "Transfers In")
    assert added["row_type"] == "transfer"
    assert added["category"] == "transfer"

    stats = reconcile_fund(corrected_path, reconcile_path, "101")
    assert stats["transfer_in"] == 5000
    assert stats["revenue_line_items"] == 0


def test_add_correction_with_explicit_total_row_type_closes_its_own_group(tmp_path: Path) -> None:
    rows_path = tmp_path / "rows.csv"
    corrections_path = tmp_path / "corrections.csv"
    corrected_path = tmp_path / "corrected.csv"
    mismatches_path = tmp_path / "mismatches.csv"

    rows_path.write_text(
        FULL_ROWS_HEADER
        + "doc,1,10,,operating,line_item,high,false,true,,,General,101,budget_table,"
        "Fund 101 General Fund expenditures,510,Supplies,,,,1000,parsed,raw\n"
        + "doc,1,12,,operating,line_item,high,false,true,,,General,101,budget_table,"
        "Fund 101 General Fund expenditures,520,Other Supplies,,,,500,parsed,raw\n",
        encoding="utf-8",
    )
    # An added Sub-Total that failed extraction, positioned (via line_number)
    # after both line items so it closes their group rather than splitting
    # it. If forced to row_type=line_item (the pre-fix behavior), it would
    # merge into whatever the next real total row's group is instead.
    corrections_path.write_text(
        FULL_CORRECTIONS_HEADER
        + "doc,1,13,add,101,Fund 101 General Fund expenditures,total,operating,,Sub-Total,,,,1500,missing,raw add\n",
        encoding="utf-8",
    )

    apply_row_corrections(rows_path, corrections_path, corrected_path)

    added_rows = list(csv.DictReader(corrected_path.open(encoding="utf-8")))
    added = next(row for row in added_rows if row["label"] == "Sub-Total")
    assert added["row_type"] == "total"

    stats = reconcile_subtotals(corrected_path, mismatches_path)
    assert stats["compared"] == 1
    assert stats["matched"] == 1
    assert stats["mismatched"] == 0
