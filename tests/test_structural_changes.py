from pathlib import Path

from budget_audit.structural_changes import (
    detect_grant_funded_capital_pairs,
    detect_whole_fund_changes,
)

DELTA_HEADER = (
    "document_id,page_number,fund_number,fund_name,budget_side,division,department,account,label,"
    "transition,old_field,new_field,old_value,new_value,absolute_delta,percent_delta,status,material\n"
)
OTHER_TRANSITION = "actual_24_25_to_budget_25_26"
HEADLINE = "headline_actual_25_26_to_budget_26_27"


def test_detect_whole_fund_changes_flags_zeroed_out_fund(tmp_path: Path) -> None:
    # Mirrors the real Fund 202 Nursing Home case: revenue and expenditure
    # both drop from materially active levels to zero.
    deltas_path = tmp_path / "deltas.csv"
    deltas_path.write_text(
        DELTA_HEADER
        + f"doc,156,202,Nursing Home,revenue,,,43120,Patient Charges,{HEADLINE},actual_25_26,budget_26_27,1611103,0,-1611103,-100,present,true\n"
        + f"doc,157,202,Nursing Home,expenditure,,,358,Remittance of Revenue Collected,{HEADLINE},actual_25_26,budget_26_27,1577453,0,-1577453,-100,present,true\n"
        # A non-headline row for the same fund should be ignored.
        + f"doc,156,202,Nursing Home,revenue,,,43120,Patient Charges,{OTHER_TRANSITION},actual_24_25,budget_25_26,1000,1611103,,,present,false\n",
        encoding="utf-8",
    )

    changes = detect_whole_fund_changes(deltas_path)

    assert len(changes) == 1
    assert changes[0].fund_number == "202"
    assert changes[0].direction == "zeroed_out"


def test_detect_whole_fund_changes_ignores_small_or_partial_funds(tmp_path: Path) -> None:
    deltas_path = tmp_path / "deltas.csv"
    deltas_path.write_text(
        DELTA_HEADER
        # Revenue drops to zero but expenditure stays active -- not a
        # whole-fund pattern.
        + f"doc,23,101,General,revenue,,,40110,Some Revenue,{HEADLINE},actual_25_26,budget_26_27,50000,0,-50000,-100,present,true\n"
        + f"doc,24,101,General,expenditure,,,50100,Some Expense,{HEADLINE},actual_25_26,budget_26_27,50000,52000,2000,4,present,false\n",
        encoding="utf-8",
    )

    changes = detect_whole_fund_changes(deltas_path)

    assert changes == []


def test_detect_grant_funded_capital_pairs_matches_comparable_magnitude(tmp_path: Path) -> None:
    # Mirrors the real Fund 172 case: no shared label prefix, but comparable
    # dollar magnitude on the grant-revenue and capital-expense sides.
    deltas_path = tmp_path / "deltas.csv"
    deltas_path.write_text(
        DELTA_HEADER
        + f"doc,153,172,Community Development,revenue,,,46980,Other State Grants - Connected Communities Facilities,{HEADLINE},actual_25_26,budget_26_27,136517,1579857,1443340,1057,present,true\n"
        + f"doc,154,172,Community Development,expenditure,,,706,Building Construction,{HEADLINE},actual_25_26,budget_26_27,151686,1755396,1603710,1057,present,true\n",
        encoding="utf-8",
    )

    pairs = detect_grant_funded_capital_pairs(deltas_path)

    assert len(pairs) == 1
    assert pairs[0].fund_number == "172"
    assert pairs[0].revenue_label == "Other State Grants - Connected Communities Facilities"
    assert pairs[0].expenditure_label == "Building Construction"


def test_detect_grant_funded_capital_pairs_rejects_mismatched_magnitude(tmp_path: Path) -> None:
    deltas_path = tmp_path / "deltas.csv"
    deltas_path.write_text(
        DELTA_HEADER
        # A small grant next to a much larger, unrelated capital project --
        # should not be paired.
        + f"doc,30,101,General,revenue,,,46980,Small Grant,{HEADLINE},actual_25_26,budget_26_27,0,30000,30000,100,new,true\n"
        + f"doc,70,101,General,expenditure,,,707,Big Unrelated Building Project,{HEADLINE},actual_25_26,budget_26_27,0,2000000,2000000,100,new,true\n",
        encoding="utf-8",
    )

    pairs = detect_grant_funded_capital_pairs(deltas_path)

    assert pairs == []
