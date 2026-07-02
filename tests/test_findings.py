import csv
from pathlib import Path

from budget_audit.findings import (
    build_findings,
    findings_from_compensation,
    findings_from_deltas,
    findings_from_reconciliation,
    write_findings,
)
from budget_audit.models import Finding

DELTA_HEADER = (
    "document_id,page_number,fund_number,fund_name,budget_side,division,department,account,label,"
    "transition,old_field,new_field,old_value,new_value,absolute_delta,percent_delta,status,material\n"
)


def test_findings_from_deltas_material_new_eliminated(tmp_path: Path) -> None:
    deltas_path = tmp_path / "deltas.csv"
    deltas_path.write_text(
        DELTA_HEADER
        + "doc,23,101,General,expenditure,,,40110,Big Increase,headline_actual_25_26_to_budget_26_27,actual_25_26,budget_26_27,10000,20000,10000,100,present,true\n"
        + "doc,23,101,General,expenditure,,,40111,New Line,headline_actual_25_26_to_budget_26_27,actual_25_26,budget_26_27,,8000,,,new,false\n"
        + "doc,24,101,General,expenditure,,,40112,Old Line,headline_actual_25_26_to_budget_26_27,actual_25_26,budget_26_27,5000,,,,eliminated,false\n"
        + "doc,24,101,General,expenditure,,,40113,Steady,headline_actual_25_26_to_budget_26_27,actual_25_26,budget_26_27,1000,1010,10,1,present,false\n"
        + "doc,24,101,General,expenditure,,,40113,Steady,actual_24_25_to_budget_25_26,actual_24_25,budget_25_26,1000,1010,10,1,present,false\n",
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
    assert all(f.category == "delta" for f in findings)


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
    assert findings[0].category == "salary"
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


def test_write_findings_round_trip(tmp_path: Path) -> None:
    out_path = tmp_path / "findings.csv"
    finding = Finding(
        finding_id="delta-101-40110",
        title="Material change: Big Increase (Fund 101)",
        category="delta",
        severity="low",
        confidence="low",
        summary="Some summary text.",
        evidence=["document=doc", "page=23"],
        open_questions=["What explains this?", "Is this recurring?"],
        status="draft",
    )

    count = write_findings([finding], out_path)
    assert count == 1

    rows = list(csv.DictReader(out_path.open(encoding="utf-8")))
    assert len(rows) == 1
    assert rows[0]["finding_id"] == "delta-101-40110"
    assert rows[0]["evidence"] == "document=doc; page=23"
    assert rows[0]["open_questions"] == "What explains this?; Is this recurring?"


def test_build_findings_combines_all_sources(tmp_path: Path) -> None:
    deltas_path = tmp_path / "deltas.csv"
    deltas_path.write_text(
        DELTA_HEADER
        + "doc,23,101,General,expenditure,,,40110,Big Increase,headline_actual_25_26_to_budget_26_27,actual_25_26,budget_26_27,10000,20000,10000,100,present,true\n",
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
        "total_findings": 3,
    }
    assert out_path.exists()
