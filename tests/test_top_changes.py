import csv
from decimal import Decimal
from pathlib import Path

from budget_audit.top_changes import (
    TopChangeConfig,
    analyze_top_changes,
    build_top_change_rows,
)

DELTA_HEADER = (
    "document_id,page_number,fund_number,fund_name,budget_side,division,department,account,label,"
    "transition,old_field,new_field,old_value,new_value,absolute_delta,percent_delta,status,material\n"
)
HEADLINE = "headline_actual_25_26_to_budget_26_27"


def test_build_top_change_rows_ranks_absolute_delta(tmp_path: Path) -> None:
    delta_path = tmp_path / "line_item_deltas.csv"
    delta_path.write_text(
        DELTA_HEADER
        + f"doc,23,101,General,expenditure,,,40110,Medium,{HEADLINE},actual_25_26,budget_26_27,10000,17000,7000,70,present,true\n"
        + f"doc,24,101,General,expenditure,,,40111,Big,{HEADLINE},actual_25_26,budget_26_27,10000,30000,20000,200,present,true\n"
        + "doc,24,101,General,expenditure,,,40112,Historical,budget_25_26,actual_24_25,budget_25_26,1,2,1,100,present,false\n",
        encoding="utf-8",
    )

    rows = build_top_change_rows(delta_path, TopChangeConfig(limit=1))

    absolute_rows = [row for row in rows if row["rank_type"] == "absolute"]
    assert len(absolute_rows) == 1
    assert absolute_rows[0]["label"] == "Big"
    assert absolute_rows[0]["rank"] == "1"


def test_build_top_change_rows_applies_percent_dollar_guardrail(tmp_path: Path) -> None:
    delta_path = tmp_path / "line_item_deltas.csv"
    delta_path.write_text(
        DELTA_HEADER
        + f"doc,23,101,General,expenditure,,,40110,Tiny Base,{HEADLINE},actual_25_26,budget_26_27,10,110,100,1000,present,false\n"
        + f"doc,24,101,General,expenditure,,,40111,Material Percent,{HEADLINE},actual_25_26,budget_26_27,10000,20000,10000,100,present,true\n",
        encoding="utf-8",
    )

    rows = build_top_change_rows(
        delta_path,
        TopChangeConfig(limit=10, min_absolute_for_percent_rank=Decimal("5000")),
    )

    percent_rows = [row for row in rows if row["rank_type"] == "percent"]
    assert [row["label"] for row in percent_rows] == ["Material Percent"]


def test_analyze_top_changes_writes_structured_output(tmp_path: Path) -> None:
    delta_path = tmp_path / "line_item_deltas.csv"
    out_path = tmp_path / "top_changes.csv"
    delta_path.write_text(
        DELTA_HEADER
        + f"doc,23,101,General,expenditure,,,40110,Big,{HEADLINE},actual_25_26,budget_26_27,10000,30000,20000,200,present,true\n",
        encoding="utf-8",
    )

    stats = analyze_top_changes(delta_path, out_path)

    assert stats["top_absolute_rows"] == 1
    assert stats["top_percent_rows"] == 1

    rows = list(csv.DictReader(out_path.open(encoding="utf-8")))
    assert rows[0]["rank_type"] == "absolute"
    assert rows[0]["evidence"] == "document=doc; page=23; fund=101 General; account=40110"
