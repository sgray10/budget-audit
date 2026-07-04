import csv
from pathlib import Path

from budget_audit.findings import (
    MANUAL_CORRECTION_DEPENDENCY_NOTE,
    build_findings,
    findings_from_compensation,
    findings_from_deltas,
    findings_from_grant_capital_pairs,
    findings_from_reconciliation,
    findings_from_structural_changes,
    write_findings,
)
from budget_audit.models import Finding, FindingStatus
from budget_audit.structural_changes import GrantFundedCapitalPair, WholeFundChange

DELTA_HEADER = (
    "document_id,page_number,fund_number,fund_name,budget_side,division,department,account,label,"
    "transition,old_field,new_field,old_value,new_value,absolute_delta,percent_delta,status,material,"
    "correction_action\n"
)


def test_findings_from_deltas_material_new_eliminated(tmp_path: Path) -> None:
    deltas_path = tmp_path / "deltas.csv"
    deltas_path.write_text(
        DELTA_HEADER
        + "doc,23,101,General,expenditure,,,40110,Big Increase,headline_actual_25_26_to_budget_26_27,actual_25_26,budget_26_27,10000,20000,10000,100,present,true,\n"
        + "doc,23,101,General,expenditure,,,40111,New Line,headline_actual_25_26_to_budget_26_27,actual_25_26,budget_26_27,,8000,,,new,false,\n"
        + "doc,24,101,General,expenditure,,,40112,Old Line,headline_actual_25_26_to_budget_26_27,actual_25_26,budget_26_27,5000,,,,eliminated,false,\n"
        + "doc,24,101,General,expenditure,,,40113,Steady,headline_actual_25_26_to_budget_26_27,actual_25_26,budget_26_27,1000,1010,10,1,present,false,\n"
        + "doc,24,101,General,expenditure,,,40113,Steady,actual_24_25_to_budget_25_26,actual_24_25,budget_25_26,1000,1010,10,1,present,false,\n",
        encoding="utf-8",
    )

    findings = findings_from_deltas(deltas_path)
    titles = {f.title for f in findings}

    assert len(findings) == 3
    assert any("New line item" in t for t in titles)
    assert any("Eliminated line item" in t for t in titles)
    assert any("Material change" in t for t in titles)
    assert not any("Steady" in t for t in titles)

    new_finding = next(f for f in findings if "New line item" in f.title)
    eliminated_finding = next(f for f in findings if "Eliminated line item" in f.title)
    material_finding = next(f for f in findings if "Material change" in f.title)

    assert new_finding.severity == "medium"
    assert eliminated_finding.severity == "medium"
    assert material_finding.severity == "low"
    # Account 40110-40113 don't fall into any specific range/label rule, so
    # all fall through to the generic review category.
    assert all(f.category == "needs_human_review" for f in findings)
    assert all(f.status == FindingStatus.MACHINE_GENERATED for f in findings)


def test_findings_from_deltas_categorizes_by_account_and_label(tmp_path: Path) -> None:
    deltas_path = tmp_path / "deltas.csv"
    deltas_path.write_text(
        DELTA_HEADER
        + "doc,23,101,General,revenue,,,46590,State Education Grant,headline_actual_25_26_to_budget_26_27,actual_25_26,budget_26_27,,50000,,,new,false,\n"
        + "doc,25,101,General,expenditure,,,707,Building Improvements,headline_actual_25_26_to_budget_26_27,actual_25_26,budget_26_27,0,100000,100000,1000,present,true,\n"
        + "doc,26,101,General,expenditure,,,399,Other Contracted Services,headline_actual_25_26_to_budget_26_27,actual_25_26,budget_26_27,1000,20000,19000,1900,present,true,\n"
        + "doc,27,101,General,expenditure,,,316,City of Dresden,headline_actual_25_26_to_budget_26_27,actual_25_26,budget_26_27,1000,20000,19000,1900,present,true,\n"
        + "doc,28,101,General,expenditure,,,502,Building & Contents Insurance,headline_actual_25_26_to_budget_26_27,actual_25_26,budget_26_27,1000,20000,19000,1900,present,true,\n",
        encoding="utf-8",
    )

    findings = findings_from_deltas(deltas_path)
    by_title = {f.title.split(":")[1].split("(")[0].strip(): f for f in findings}

    assert by_title["State Education Grant"].category == "grant_or_intergovernmental_revenue"
    assert by_title["Building Improvements"].category == "capital_project"
    assert by_title["Other Contracted Services"].category == "contracted_services"
    assert by_title["City of Dresden"].category == "allocation_or_recipient_payment"
    # The classification bug this feature exists to fix: an insurance line
    # containing the word "Building" must not land in capital_project.
    assert by_title["Building & Contents Insurance"].category == "insurance_or_claims"


def test_findings_from_deltas_flags_manual_correction_dependency(tmp_path: Path) -> None:
    deltas_path = tmp_path / "deltas.csv"
    deltas_path.write_text(
        DELTA_HEADER
        + "doc,23,101,General,expenditure,,,40110,Big Increase,headline_actual_25_26_to_budget_26_27,actual_25_26,budget_26_27,10000,20000,10000,100,present,true,add\n",
        encoding="utf-8",
    )

    findings = findings_from_deltas(deltas_path)

    assert len(findings) == 1
    assert MANUAL_CORRECTION_DEPENDENCY_NOTE in findings[0].summary


def test_findings_from_compensation_only_needs_review(tmp_path: Path) -> None:
    flags_path = tmp_path / "flags.csv"
    flags_path.write_text(
        "document_id,page_number,fund_number,fund_name,department,division,account,label,budget_26_27,classification\n"
        "doc,23,101,General,Sheriff,,50100,Social Security,5000,aggregate\n"
        "doc,23,101,General,Sheriff,,50101,Registrar's Salary Supplement,3500,needs_review\n",
        encoding="utf-8",
    )

    findings = findings_from_compensation(flags_path)

    assert len(findings) == 1
    assert findings[0].category == "personnel"
    assert "Registrar's Salary Supplement" in findings[0].title


def test_findings_from_reconciliation_flags_out_of_tolerance(tmp_path: Path) -> None:
    out_of_tolerance = tmp_path / "reconcile_101.csv"
    out_of_tolerance.write_text("metric,value\nnet_with_transfers,-4407\n", encoding="utf-8")

    within_tolerance = tmp_path / "reconcile_116.csv"
    within_tolerance.write_text("metric,value\nnet_with_transfers,10\n", encoding="utf-8")

    findings = findings_from_reconciliation(
        {"101": out_of_tolerance, "116": within_tolerance}, tolerance=100
    )

    assert len(findings) == 1
    assert findings[0].category == "reconciliation"
    assert "Fund 101" in findings[0].title


def test_findings_from_structural_changes() -> None:
    change = WholeFundChange(
        fund_number="202",
        fund_name="Nursing Home",
        direction="zeroed_out",
        revenue_old=1633722,
        revenue_new=0,
        expenditure_old=1627354,
        expenditure_new=0,
        sample_labels=["Patient Charges"],
    )

    findings = findings_from_structural_changes([change])

    assert len(findings) == 1
    assert findings[0].category == "whole_fund_structural_change"
    assert "202" in findings[0].title


def test_findings_from_grant_capital_pairs() -> None:
    pair = GrantFundedCapitalPair(
        fund_number="172",
        fund_name="Community Development",
        revenue_label="Other State Grants - Connected Communities Facilities",
        revenue_delta=1443340,
        expenditure_label="Building Construction",
        expenditure_delta=1603710,
    )

    findings = findings_from_grant_capital_pairs([pair])

    assert len(findings) == 1
    assert findings[0].category == "grant_funded_capital_project"
    assert "172" in findings[0].title


def test_write_findings_round_trip(tmp_path: Path) -> None:
    out_path = tmp_path / "findings.csv"
    finding = Finding(
        finding_id="delta-101-40110",
        title="Material change: Big Increase (Fund 101)",
        category="needs_human_review",
        severity="low",
        confidence="low",
        summary="Some summary text.",
        evidence=["document=doc", "page=23"],
        open_questions=["What explains this?", "Is this recurring?"],
        cluster_id="101-BIG",
    )

    count = write_findings([finding], out_path)
    assert count == 1

    rows = list(csv.DictReader(out_path.open(encoding="utf-8")))
    assert len(rows) == 1
    assert rows[0]["finding_id"] == "delta-101-40110"
    assert rows[0]["evidence"] == "document=doc; page=23"
    assert rows[0]["open_questions"] == "What explains this?; Is this recurring?"
    assert rows[0]["status"] == "machine_generated"
    assert rows[0]["cluster_id"] == "101-BIG"


def test_build_findings_combines_all_sources(tmp_path: Path) -> None:
    deltas_path = tmp_path / "deltas.csv"
    deltas_path.write_text(
        DELTA_HEADER
        + "doc,23,101,General,expenditure,,,40110,Big Increase,headline_actual_25_26_to_budget_26_27,actual_25_26,budget_26_27,10000,20000,10000,100,present,true,\n",
        encoding="utf-8",
    )

    flags_path = tmp_path / "flags.csv"
    flags_path.write_text(
        "document_id,page_number,fund_number,fund_name,department,division,account,label,budget_26_27,classification\n"
        "doc,23,101,General,Sheriff,,50101,Registrar's Salary Supplement,3500,needs_review\n",
        encoding="utf-8",
    )

    reconcile_path = tmp_path / "reconcile_101.csv"
    reconcile_path.write_text("metric,value\nnet_with_transfers,-4407\n", encoding="utf-8")

    out_path = tmp_path / "findings.csv"
    stats = build_findings(deltas_path, flags_path, {"101": reconcile_path}, out_path)

    assert stats == {
        "delta_findings": 1,
        "compensation_findings": 1,
        "reconciliation_findings": 1,
        "structural_change_findings": 0,
        "grant_capital_pair_findings": 0,
        "total_findings": 3,
    }
    assert out_path.exists()


def test_build_findings_includes_structural_and_grant_capital_findings(tmp_path: Path) -> None:
    deltas_path = tmp_path / "deltas.csv"
    deltas_path.write_text(DELTA_HEADER, encoding="utf-8")

    flags_path = tmp_path / "flags.csv"
    flags_path.write_text(
        "document_id,page_number,fund_number,fund_name,department,division,account,label,budget_26_27,classification\n",
        encoding="utf-8",
    )

    out_path = tmp_path / "findings.csv"
    change = WholeFundChange(
        fund_number="202",
        fund_name="Nursing Home",
        direction="zeroed_out",
        revenue_old=1000000,
        revenue_new=0,
        expenditure_old=1000000,
        expenditure_new=0,
        sample_labels=[],
    )
    pair = GrantFundedCapitalPair(
        fund_number="172",
        fund_name="Community Development",
        revenue_label="Grant",
        revenue_delta=100000,
        expenditure_label="Construction",
        expenditure_delta=110000,
    )

    stats = build_findings(
        deltas_path,
        flags_path,
        {},
        out_path,
        whole_fund_changes=[change],
        grant_capital_pairs=[pair],
    )

    assert stats["structural_change_findings"] == 1
    assert stats["grant_capital_pair_findings"] == 1
    assert stats["total_findings"] == 2
