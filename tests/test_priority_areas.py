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


def _nursing_home_change() -> WholeFundChange:
    return WholeFundChange(
        fund_number="202",
        fund_name="Nursing Home",
        direction="zeroed_out",
        revenue_old=Decimal("1633722"),
        revenue_new=Decimal("0"),
        expenditure_old=Decimal("1627354"),
        expenditure_new=Decimal("0"),
        sample_labels=["Patient Charges"],
        sample_lines=("page=156 account=43120 label=Patient Charges 1611103 -> 0",),
    )


def test_priority_areas_cross_link_nursing_home_to_fund_101_nh_lines(tmp_path: Path) -> None:
    from budget_audit.related_items import build_label_index

    rows_path = tmp_path / "rows.csv"
    rows_path.write_text(
        "document_id,page_number,row_type,fund_number,fund_name,account,label\n"
        "doc,24,line_item,101,General,44110,NH Investment Income - Nursing Home Funds\n"
        "doc,27,line_item,101,General,48130,NH Contributions - Nursing Home\n"
        "doc,156,line_item,202,Nursing Home,43120,Patient Charges\n",
        encoding="utf-8",
    )
    label_index = build_label_index(rows_path)

    areas = build_priority_areas(None, [_nursing_home_change()], [], [], label_index=label_index)

    assert len(areas) == 1
    descriptions = [item.description for item in areas[0].related_items]
    assert any("NH Investment Income - Nursing Home Funds" in d for d in descriptions)
    assert any("NH Contributions - Nursing Home" in d for d in descriptions)
    # The records request mentions the related lines rather than ignoring them.
    assert "include any related lines in other funds" in areas[0].first_records_request


def test_priority_areas_populate_why_normal_and_records_request() -> None:
    areas = build_priority_areas(None, [_nursing_home_change()], [], [])

    assert len(areas) == 1
    area = areas[0]
    assert "may reflect activity moving to another fund" in area.why_normal
    assert "commission minutes" in area.first_records_request
    # Evidence carries the per-line detail, not just the fund number.
    assert any("page=156" in item for item in area.evidence)


def test_priority_areas_cluster_evidence_includes_key_lines(tmp_path: Path) -> None:
    clusters_path = tmp_path / "clusters.csv"
    clusters_path.write_text(
        "cluster_id,fund_number,fund_name,prefix,revenue_total,expenditure_total,"
        "capital_expenditure_total,is_paired,line_item_count,sample_labels,cluster_type,narrative,"
        "key_revenue_line,key_expenditure_line\n"
        '151-JAIL,151,Debt Service,JAIL,0,559219,0,false,2,"JAIL Principal on Notes",debt_service,'
        '"debt narrative","","page=145 account=602 label=JAIL Principal on Notes budget_26_27=470000"\n',
        encoding="utf-8",
    )

    areas = build_priority_areas(clusters_path, [], [], [])

    assert len(areas) == 1
    assert any("page=145" in item for item in areas[0].evidence)
    assert "Debt schedule" in areas[0].first_records_request
