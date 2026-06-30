from budget_audit.summarize import budget_side_from_section, parse_amount


def test_parse_amount_plain_integer() -> None:
    assert parse_amount("14,013,957") == 14013957


def test_parse_amount_parentheses_negative() -> None:
    assert parse_amount("(1,689)") == -1689


def test_parse_amount_invalid() -> None:
    assert parse_amount("not-a-number") is None


def test_budget_side_revenue() -> None:
    assert budget_side_from_section("Fund 101 General Fund revenues") == "revenue"


def test_budget_side_default_expenditure() -> None:
    assert budget_side_from_section("Fund 101 General Fund expenditures") == "expenditure"
