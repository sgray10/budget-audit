from pathlib import Path

from budget_audit.reconcile import budget_side_from_section, parse_amount, reconcile_fund


def test_parse_amount() -> None:
    assert parse_amount("14,013,957") == 14013957
    assert parse_amount("(1,689)") == -1689
    assert parse_amount("not-a-number") is None


def test_budget_side_from_section() -> None:
    assert budget_side_from_section("Fund 101 General Fund revenues") == "revenue"
    assert budget_side_from_section("Fund 101 General Fund summary") == "summary"
    assert budget_side_from_section("Fund 101 General Fund expenditures") == "expenditure"


def test_reconcile_fund(tmp_path: Path) -> None:
    rows_path = tmp_path / "rows.csv"
    out_path = tmp_path / "reconcile.csv"

    rows_path.write_text(
        "fund_number,section_hint,row_type,label,budget_26_27\n"
        "101,Fund 101 General Fund revenues,line_item,Current Tax,100\n"
        "101,Fund 101 General Fund revenues,transfer,Transfers In,25\n"
        "101,Fund 101 General Fund expenditures,line_item,Supplies,90\n"
        "101,Fund 101 General Fund expenditures,transfer,Transfers to Other Funds,5\n"
        "116,Fund 116 Solid Waste/Sanitation,line_item,Supplies,999\n",
        encoding="utf-8",
    )

    stats = reconcile_fund(rows_path, out_path, "101")

    assert stats["revenue_line_items"] == 100
    assert stats["transfer_in"] == 25
    assert stats["revenue_with_transfers"] == 125
    assert stats["expenditure_line_items"] == 90
    assert stats["transfer_out"] == 5
    assert stats["expenditure_with_transfers"] == 95
    assert stats["net_with_transfers"] == 30
    assert out_path.exists()
