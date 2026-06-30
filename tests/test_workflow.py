from pathlib import Path

from budget_audit.workflow import parse_fund_list, reviewed_range_paths, safe_page_label


def test_safe_page_label() -> None:
    assert safe_page_label("23-85") == "23_85"
    assert safe_page_label("23,25-27") == "23_25_27"
    assert safe_page_label("23, 25-27") == "23_25_27"


def test_parse_fund_list() -> None:
    assert parse_fund_list("101,116, 131") == ["101", "116", "131"]
    assert parse_fund_list("101,,131") == ["101", "131"]


def test_reviewed_range_paths(tmp_path: Path) -> None:
    paths = reviewed_range_paths(tmp_path, "23-85")

    assert paths.raw_rows == tmp_path / "ocr_table_rows_23_85.csv"
    assert paths.enriched_rows == tmp_path / "ocr_table_rows_23_85_enriched.csv"
    assert paths.classified_rows == tmp_path / "ocr_table_rows_23_85_classified.csv"
    assert paths.corrected_rows == tmp_path / "ocr_table_rows_23_85_corrected.csv"
    assert paths.review_queue == tmp_path / "ocr_review_queue_23_85_corrected.csv"
