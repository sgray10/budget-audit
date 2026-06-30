from budget_audit.ocr_table_rows import clean_ocr_amount, classify_raw_line


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
