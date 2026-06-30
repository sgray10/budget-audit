from pathlib import Path

from budget_audit.corrections import apply_row_corrections


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

    assert stats == {"input_rows": 1, "output_rows": 2, "replaced": 1, "added": 1}
    assert "11000" in output
    assert "Unemployment Compensation" in output
    assert "manual_correction" in output
