from decimal import Decimal
from pathlib import Path

from budget_audit.data_quality import DataQualityWarning
from budget_audit.priority_areas import build_priority_areas
from budget_audit.structural_changes import GrantFundedCapitalPair, WholeFundChange

CLUSTERS_HEADER = (
    "cluster_id,fund_number,fund_name,prefix,revenue_total,expenditure_total,is_paired,"
    "line_item_count,sample_labels,cluster_type,narrative\n"
)


def test_build_priority_areas_includes_structural_changes_first(tmp_path: Path) -> None:
    change = WholeFundChange(
        fund_number="202",
        fund_name="Nursing Home",
        direction="zeroed_out",
        revenue_old=Decimal("1633722"),
        revenue_new=Decimal("0"),
        expenditure_old=Decimal("1627354"),
        expenditure_new=Decimal("0"),
        sample_labels=["Patient Charges"],
    )

    areas = build_priority_areas(None, [change], [], [])

    assert len(areas) == 1
    assert areas[0].pattern == "structural_change"
    assert "202" in areas[0].funds


def test_build_priority_areas_dedupes_cluster_against_fund_level_pair(tmp_path: Path) -> None:
    clusters_path = tmp_path / "clusters.csv"
    clusters_path.write_text(
        CLUSTERS_HEADER
        + "172-CD,172,Community Development,CD,1443340,1603710,true,2,\"Grant; Construction\","
        "grant_funded_capital_project,\"narrative text\"\n",
        encoding="utf-8",
    )
    pair = GrantFundedCapitalPair(
        fund_number="172",
        fund_name="Community Development",
        revenue_label="Other State Grants - Connected Communities Facilities",
        revenue_delta=Decimal("1443340"),
        expenditure_label="Building Construction",
        expenditure_delta=Decimal("1603710"),
    )

    areas = build_priority_areas(clusters_path, [], [pair], [])

    # Only the fund-level pair should appear, not a duplicate cluster-based
    # entry for the same fund's grant_funded_capital_project cluster.
    fund_172_areas = [a for a in areas if "172" in a.funds]
    assert len(fund_172_areas) == 1
    assert fund_172_areas[0].pattern == "paired_revenue_expense"


def test_build_priority_areas_reserves_slots_for_debt_and_allocation_clusters(tmp_path: Path) -> None:
    clusters_path = tmp_path / "clusters.csv"
    rows = [CLUSTERS_HEADER]
    # Several large grant-program clusters that would otherwise crowd out a
    # much smaller debt-service cluster on pure dollar magnitude.
    for i in range(5):
        rows.append(
            f"141-G{i},141,General Purpose School,G{i},{500000 - i},{500000 - i},true,5,\"label\","
            "grant_funded_program,\"narrative\"\n"
        )
    rows.append(
        "151-JAIL,151,Debt Service,JAIL,0,50000,false,2,\"JAIL Principal\",debt_service,\"debt narrative\"\n"
    )
    clusters_path.write_text("".join(rows), encoding="utf-8")

    areas = build_priority_areas(clusters_path, [], [], [], limit=5)

    assert any(a.pattern == "one_sided" and "151" in a.funds for a in areas)


def test_build_priority_areas_flags_manual_correction_dependency(tmp_path: Path) -> None:
    change = WholeFundChange(
        fund_number="202",
        fund_name="Nursing Home",
        direction="zeroed_out",
        revenue_old=Decimal("1000000"),
        revenue_new=Decimal("0"),
        expenditure_old=Decimal("1000000"),
        expenditure_new=Decimal("0"),
        sample_labels=[],
    )

    areas = build_priority_areas(None, [change], [], [], manual_correction_funds={"202"})

    assert areas[0].depends_on_manual_correction is True


def test_build_priority_areas_includes_data_quality_group(tmp_path: Path) -> None:
    warning = DataQualityWarning(
        warning_id="dq-1",
        warning_type="unparsed_amount",
        severity="high",
        confidence="high",
        summary="x",
        evidence=[],
        fund_number="101",
    )

    areas = build_priority_areas(None, [], [], [warning])

    assert len(areas) == 1
    assert areas[0].pattern == "data_quality_driven"
    assert "101" in areas[0].funds
