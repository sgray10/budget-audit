import csv
from pathlib import Path

from budget_audit.ocr_table_rows import clean_ocr_amount, classify_raw_line, extract_ocr_table_rows


def test_clean_ocr_amount_removes_split_thousands() -> None:
    assert clean_ocr_amount("48    800") == "48800"


def test_clean_ocr_amount_replaces_section_symbol_artifact() -> None:
    assert clean_ocr_amount("§22") == "522"


def test_classify_raw_line_account_row() -> None:
    line = "40110 Current Tax 3,901,293 5,356,500 5,649,354 5,454,100"
    assert classify_raw_line(line) == "account_row"


def test_classify_raw_line_header_or_context() -> None:
    assert classify_raw_line("Fund Number: 101") == "header_or_context"


def test_classify_raw_line_account_group() -> None:
    assert classify_raw_line("40100") == "account_group"


def test_clean_ocr_amount_replaces_decimal_thousands_artifact() -> None:
    assert clean_ocr_amount("4.037") == "4,037"


def test_classify_raw_line_total_row() -> None:
    line = "Sub-Total 15,142,886 16,551,008 16,980,613 16,636,270"
    assert classify_raw_line(line) == "total_row"


def test_classify_raw_line_total_expense_row() -> None:
    line = "Total Expense 20,636,149 22,488,876 23,164,553 23,323,471"
    assert classify_raw_line(line) == "total_row"


def test_classify_raw_line_account_row_takes_precedence_over_total() -> None:
    # Account rows are matched first; a total-like label would never appear
    # with a leading digit account in real data, but confirm no ambiguity.
    line = "40110 Total Adjustment 100 200 300 400"
    assert classify_raw_line(line) == "account_row"


def test_extract_ocr_table_rows_extracts_total_row(tmp_path: Path) -> None:
    ocr_dir = tmp_path / "ocr"
    ocr_dir.mkdir()
    (ocr_dir / "page-001.txt").write_text(
        "Fund Number: 101\n"
        "40110 Current Tax 3,901,293 5,356,500 5,649,354 5,454,100\n"
        "40120 Trustee's Collection 82,172 45,000 62,281 55,000\n"
        "Sub-Total 3,983,465 5,401,500 5,711,635 5,509,100\n",
        encoding="utf-8",
    )

    out_path = tmp_path / "rows.csv"
    count = extract_ocr_table_rows(ocr_dir, out_path, "doc")

    assert count == 3
    rows = list(csv.DictReader(out_path.open(encoding="utf-8")))
    total_rows = [row for row in rows if row["label"] == "Sub-Total"]
    assert len(total_rows) == 1
    assert total_rows[0]["account"] == ""
    assert total_rows[0]["budget_26_27"] == "5,509,100"
    line_item_rows = [row for row in rows if row["account"] != ""]
    assert len(line_item_rows) == 2
