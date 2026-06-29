from decimal import Decimal

from budget_audit.normalize import (
    classify_amount_column,
    extract_account_code,
    looks_salary_related,
    normalize_whitespace,
    parse_amount,
)


def test_normalize_whitespace() -> None:
    assert normalize_whitespace("  Current   Tax \n  ") == "Current Tax"


def test_parse_amount() -> None:
    assert parse_amount("5,454,100") == Decimal("5454100")
    assert parse_amount("$1,234.50") == Decimal("1234.50")
    assert parse_amount("(1,689)") == Decimal("-1689")
    assert parse_amount("-") is None


def test_extract_account_code() -> None:
    assert extract_account_code("40110 Current Tax") == "40110"
    assert extract_account_code("Current Tax") is None


def test_classify_amount_column() -> None:
    assert classify_amount_column("Actual 24-25") == "actual"
    assert classify_amount_column("Budget 26-27") == "budget"


def test_looks_salary_related() -> None:
    assert looks_salary_related("Regular Salaries")
    assert looks_salary_related("Employee Insurance")
    assert not looks_salary_related("Current Tax")
