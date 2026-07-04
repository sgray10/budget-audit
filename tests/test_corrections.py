from pathlib import Path

import pytest

from budget_audit.corrections import apply_row_corrections

ROWS_HEADER = "document_id,page_number,account,label,budget_26_27,raw_line\n"
CORRECTIONS_HEADER = "document_id,page_number,action,account,label,budget_26_27,reason,raw_line\n"


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
