import csv
from decimal import Decimal
from pathlib import Path

from budget_audit.analyze import (
    MaterialityThreshold,
    analyze_deltas,
    is_material,
    line_status,
)

ROW_HEADER = (
    "document_id,page_number,row_type,fund_number,fund_name,section_hint,"
    "division,department,account,label,actual_24_25,budget_25_26,actual_25_26,budget_26_27\n"
)


def test_is_material_absolute_threshold() -> None:
    # require_both=False isolates the absolute-dollar check from the percent check.
    threshold = MaterialityThreshold(min_absolute=Decimal("5000"), min_percent=Decimal("15"), require_both=False)
    assert is_material(Decimal("5000"), Decimal("1"), threshold) is True
    assert is_material(Decimal("4999"), Decimal("1"), threshold) is False


def test_is_material_percent_threshold() -> None:
    # require_both=False isolates the percent check from the absolute-dollar check.
    threshold = MaterialityThreshold(min_absolute=Decimal("999999"), min_percent=Decimal("15"), require_both=False)
    assert is_material(Decimal("100"), Decimal("20"), threshold) is True
    assert is_material(Decimal("100"), Decimal("10"), threshold) is False


def test_is_material_either_vs_require_both() -> None:
    either = MaterialityThreshold(min_absolute=Decimal("5000"), min_percent=Decimal("50"), require_both=False)
    assert is_material(Decimal("6000"), Decimal("1"), either) is True

    both = MaterialityThreshold(min_absolute=Decimal("5000"), min_percent=Decimal("50"), require_both=True)
    assert is_material(Decimal("6000"), Decimal("1"), both) is False
    assert is_material(Decimal("6000"), Decimal("60"), both) is True


def test_is_material_default_requires_both() -> None:
    # The project default is require_both=True: a large percent swing on a
    # tiny dollar amount alone should not be flagged, to avoid drowning
    # meaningful changes in small-dollar noise.
    threshold = MaterialityThreshold(min_absolute=Decimal("5000"), min_percent=Decimal("15"))
    assert is_material(Decimal("100"), Decimal("50"), threshold) is False
    assert is_material(Decimal("6000"), Decimal("20"), threshold) is True


def test_is_material_zero_old_value_uses_absolute_only() -> None:
    threshold = MaterialityThreshold(min_absolute=Decimal("5000"), min_percent=Decimal("15"))
    # material_delta(Decimal(0), Decimal(6000)) returns (6000, None)
    assert is_material(Decimal("6000"), None, threshold) is True
    assert is_material(Decimal("100"), None, threshold) is False


def test_is_material_none_absolute_is_never_material() -> None:
    threshold = MaterialityThreshold()
    assert is_material(None, None, threshold) is False


def test_line_status() -> None:
    assert line_status("", "") == "blank_both"
    assert line_status("", "1,000") == "new"
    assert line_status("1,000", "") == "eliminated"
    assert line_status("1,000", "2,000") == "present"


def test_analyze_deltas_material_new_eliminated_unchanged(tmp_path: Path) -> None:
    rows_path = tmp_path / "rows.csv"
    out_dir = tmp_path / "out"

    rows_path.write_text(
        ROW_HEADER
        + "doc,23,line_item,101,General,Fund 101 General Fund expenditures,,,40110,Big Increase,,,\"10,000\",\"20,000\"\n"
        + "doc,23,line_item,101,General,Fund 101 General Fund expenditures,,,40111,New Line,,,,\"8,000\"\n"
        + "doc,24,line_item,101,General,Fund 101 General Fund expenditures,,,40112,Old Line,,,\"5,000\",\n"
        + "doc,24,line_item,101,General,Fund 101 General Fund expenditures,,,40113,Steady,,,\"1,000\",\"1,010\"\n"
        + "doc,24,transfer,101,General,Fund 101 General Fund expenditures,,,40114,Transfers Out,,,\"1,000\",\"5,000\"\n",
        encoding="utf-8",
    )

    stats = analyze_deltas(rows_path, out_dir, MaterialityThreshold(min_absolute=Decimal("5000"), min_percent=Decimal("15")))

    assert stats["line_items"] == 4
    assert stats["new_line_rows"] == 1
    assert stats["eliminated_line_rows"] == 1

    delta_rows = list(csv.DictReader((out_dir / "line_item_deltas.csv").open(encoding="utf-8")))
    headline_rows = {row["label"]: row for row in delta_rows if row["transition"] == "headline_actual_25_26_to_budget_26_27"}

    assert headline_rows["Big Increase"]["status"] == "present"
    assert headline_rows["Big Increase"]["material"] == "true"
    assert headline_rows["New Line"]["status"] == "new"
    assert headline_rows["Old Line"]["status"] == "eliminated"
    assert headline_rows["Steady"]["material"] == "false"

    # transfer rows are excluded entirely (row_type != line_item)
    assert "Transfers Out" not in {row["label"] for row in delta_rows}

    summary_rows = list(csv.DictReader((out_dir / "delta_summary_by_fund.csv").open(encoding="utf-8")))
    assert len(summary_rows) == 1
    assert summary_rows[0]["fund_number"] == "101"
    assert summary_rows[0]["material_count"] == "1"
    assert summary_rows[0]["total_absolute_delta"] == "10010"
