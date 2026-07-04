from budget_audit.review import (
    account_looks_suspicious,
    amount_looks_suspicious,
    review_reasons,
)


def test_amount_accepts_commas() -> None:
    assert amount_looks_suspicious("14,013,957") is False


def test_amount_flags_section_symbol() -> None:
    assert amount_looks_suspicious("§22") is True


def test_account_accepts_budget_codes() -> None:
    assert account_looks_suspicious("40110") is False


def test_account_flags_non_digit() -> None:
    assert account_looks_suspicious("4O110") is True


def test_review_reasons_flags_short_label() -> None:
    row = {
        "account": "40110",
        "label": "",
        "raw_line": "40110 1 2 3 4",
        "actual_24_25": "1",
        "budget_25_26": "2",
        "actual_25_26": "3",
        "budget_26_27": "4",
        "fund_number": "101",
        "section_hint": "Fund 101 General Fund revenues",
        "parse_status": "parsed",
    }
    assert "short_or_missing_label" in review_reasons(row)


def test_review_reasons_does_not_flag_blank_account_on_total_row() -> None:
    row = {
        "account": "",
        "label": "Sub-Total",
        "raw_line": "Sub-Total 100 200 300 400",
        "actual_24_25": "100",
        "budget_25_26": "200",
        "actual_25_26": "300",
        "budget_26_27": "400",
        "fund_number": "143",
        "section_hint": "Fund 143 Child Nutrition expenditures",
        "parse_status": "parsed",
        "row_type": "total",
    }
    assert "suspicious_account" not in review_reasons(row)


def test_review_reasons_flags_blank_account_on_line_item_row() -> None:
    row = {
        "account": "",
        "label": "Some Line",
        "raw_line": "Some Line 100 200 300 400",
        "actual_24_25": "100",
        "budget_25_26": "200",
        "actual_25_26": "300",
        "budget_26_27": "400",
        "fund_number": "143",
        "section_hint": "Fund 143 Child Nutrition expenditures",
        "parse_status": "parsed",
        "row_type": "line_item",
    }
    assert "suspicious_account" in review_reasons(row)
