from budget_audit.row_classify import classify_category, classify_row


def test_classify_transfer_row() -> None:
    assert classify_row("Transfers In", "49800") == "transfer"


def test_classify_fund_balance_row() -> None:
    assert classify_row("Unassigned Fund Balance", "39000") == "fund_balance"


def test_classify_total_row() -> None:
    assert classify_row("Total Expenditures", "59999") == "total"


def test_classify_line_item_row() -> None:
    assert classify_row("Current Tax", "40110") == "line_item"


def test_classify_compensation_category() -> None:
    assert classify_category("Medical Insurance") == "compensation"
