import re
from decimal import Decimal
from pathlib import Path

from budget_audit.report import (
    format_money,
    load_reconcile_summary,
    markdown_table,
    reconciliation_status,
    render_appendix_data_quality,
    render_appendix_raw_findings,
    render_executive_summary,
    render_findings_section,
    render_high_impact_data_quality_section,
    render_priority_areas_section,
    render_public_records_section,
    render_report,
    render_reconciliation_section,
    render_scope_section,
    render_top_absolute_changes_section,
    render_top_clusters_section,
    render_top_percentage_changes_section,
)

BANNED_WORDS = re.compile(r"\bhidden\b|\bsuspicious\b|\bwrong\b|\breconciled\b", re.IGNORECASE)

FINDINGS_HEADER = "finding_id,title,category,severity,confidence,summary,evidence,open_questions,status\n"
DATA_QUALITY_HEADER = (
    "warning_id,warning_type,severity,confidence,summary,evidence,status,document_id,page_number,"
    "fund_number,account,amount,impact_score\n"
)
CLUSTERS_HEADER = (
    "cluster_id,fund_number,fund_name,prefix,revenue_total,expenditure_total,is_paired,"
    "line_item_count,sample_labels,cluster_type,narrative\n"
)


def test_format_money() -> None:
    assert format_money(None) == ""
    assert format_money(Decimal("1234.5")) == "$1,234.50"


def test_markdown_table() -> None:
    table = markdown_table(["A", "B"], [["1", "2"]])
    assert table == "| A | B |\n| --- | --- |\n| 1 | 2 |"


def test_render_scope_section_lists_full_packet_scope() -> None:
    section = render_scope_section()
    for fund in ["101", "116", "122", "131", "141", "143", "151", "171", "172", "202"]:
        assert fund in section
    assert "pages 23-158" in section


def test_reconciliation_status_never_says_reconciled() -> None:
    assert reconciliation_status(Decimal("100"), Decimal("100"), Decimal("0")) == "balanced_in_extraction"
    assert reconciliation_status(Decimal("1000000"), Decimal("1000000"), Decimal("-500")) == "extracted_with_gap"
    assert (
        reconciliation_status(Decimal("1021582"), Decimal("1261204"), Decimal("-239622"))
        == "needs_reconciliation_review"
    )
    for status in ("balanced_in_extraction", "extracted_with_gap", "needs_reconciliation_review"):
        assert "reconciled" not in status


def test_load_reconcile_summary_computes_status(tmp_path: Path) -> None:
    path = tmp_path / "reconcile_101.csv"
    path.write_text(
        "metric,value\nrevenue_with_transfers,14057984\nexpenditure_with_transfers,14062391\n"
        "net_with_transfers,-4407\n",
        encoding="utf-8",
    )

    summary = load_reconcile_summary("101", path)

    assert summary["fund_number"] == "101"
    assert summary["fund_name"] == "General"
    assert summary["revenue"] == "14057984"
    assert summary["expenditure"] == "14062391"
    assert summary["net"] == "-4407"
    assert summary["status"] == "extracted_with_gap"


def test_render_reconciliation_section_does_not_call_nonzero_net_reconciled() -> None:
    summaries = [
        {
            "fund_number": "151",
            "fund_name": "Debt Service",
            "revenue": "1021582",
            "expenditure": "1261204",
            "net": "-239622",
            "status": "needs_reconciliation_review",
        }
    ]

    section = render_reconciliation_section(summaries)

    assert "## Reconciliation summary" in section
    assert "needs reconciliation review" in section.lower()
    assert not BANNED_WORDS.search(section)


def test_render_executive_summary_is_neutral_and_mentions_areas() -> None:
    summaries = [
        {"fund_number": "101", "fund_name": "General", "revenue": "100", "expenditure": "100", "net": "0", "status": "balanced_in_extraction"}
    ]
    section = render_executive_summary(summaries, ["Fund 202 Nursing Home fund-wide change"], 3)

    assert "## Executive summary" in section
    assert "does not assert wrongdoing" in section
    assert "Fund 202 Nursing Home fund-wide change" in section
    assert not BANNED_WORDS.search(section)


def test_render_priority_areas_section(tmp_path: Path) -> None:
    priority_areas_path = tmp_path / "priority_areas.csv"
    priority_areas_path.write_text(
        "priority_area_id,title,funds,why_it_matters,dollar_amounts,pattern,questions,evidence,"
        "depends_on_manual_correction\n"
        'structural-202,"Fund 202 Nursing Home fund-wide change",202,"Revenue and expenditure both drop.",'
        '"revenue 100 -> 0",structural_change,"Does this fund remain active?","fund=202",true\n',
        encoding="utf-8",
    )

    section = render_priority_areas_section(priority_areas_path)

    assert "## Priority follow-up areas" in section
    assert "Fund 202 Nursing Home fund-wide change" in section
    assert "depends on a traceable manual correction" in section
    assert not BANNED_WORDS.search(section)


def test_render_priority_areas_section_empty() -> None:
    assert "No priority follow-up areas" in render_priority_areas_section(None)


def test_render_findings_section_caps_examples_and_points_to_appendix(tmp_path: Path) -> None:
    findings_path = tmp_path / "findings.csv"
    rows = "".join(
        f'nhr-{i},"Material change: Item {i} (Fund 101)",needs_human_review,low,low,'
        f'"Needs explanation.","document=doc; page=23","What explains this?",machine_generated\n'
        for i in range(5)
    )
    findings_path.write_text(FINDINGS_HEADER + rows, encoding="utf-8")

    section = render_findings_section(findings_path, examples_per_category=3)

    assert "Other material changes needing review (5)" in section
    assert "Item 0" in section
    assert "Item 2" in section
    assert "Item 4" not in section
    assert "2 more" in section
    assert not BANNED_WORDS.search(section)


def test_render_appendix_raw_findings_lists_everything(tmp_path: Path) -> None:
    findings_path = tmp_path / "findings.csv"
    rows = "".join(
        f'nhr-{i},"Material change: Item {i} (Fund 101)",needs_human_review,low,low,'
        f'"Needs explanation.","document=doc; page=23","What explains this?",machine_generated\n'
        for i in range(5)
    )
    findings_path.write_text(FINDINGS_HEADER + rows, encoding="utf-8")

    section = render_appendix_raw_findings(findings_path)

    assert "## Appendix A" in section
    for i in range(5):
        assert f"Item {i}" in section


def test_render_top_clusters_section_ranks_by_magnitude_and_has_narrative(tmp_path: Path) -> None:
    clusters_path = tmp_path / "clusters.csv"
    clusters_path.write_text(
        CLUSTERS_HEADER
        + "101-OPID,101,General,OPID,90954,123500,true,14,OPID Opioid Settlement Funds,allocation_program,"
        "\"Fund 101 General cluster 'OPID' allocates funds to named recipients.\"\n"
        "101-BONUS,101,General,BONUS,0,5000,false,3,BONUS Social Security,personnel_or_benefits,"
        "\"Fund 101 General cluster 'BONUS' is a personnel/benefits grouping.\"\n",
        encoding="utf-8",
    )

    section = render_top_clusters_section(clusters_path)

    assert "## Top clusters" in section
    assert "OPID" in section
    assert "BONUS" in section
    # OPID has the larger combined magnitude (214,454 vs 5,000), so it should
    # appear first in the ranked table.
    assert section.index("OPID") < section.index("BONUS")
    assert "What these clusters appear to represent" in section
    assert "allocates funds to named recipients" in section
    assert not BANNED_WORDS.search(section)


def test_render_top_clusters_section_empty() -> None:
    assert "No clusters" in render_top_clusters_section(None)


def test_render_public_records_section_dedupes_within_category(tmp_path: Path) -> None:
    findings_path = tmp_path / "findings.csv"
    findings_path.write_text(
        FINDINGS_HEADER
        + 'grant-1,"New line item: State Grant (Fund 101)",grant_or_intergovernmental_revenue,medium,low,'
        '"Needs explanation.","document=doc; page=23",'
        '"Please provide the grant award letter, grant budget, match requirements, approved spending plan, and reporting requirements.",machine_generated\n'
        + 'grant-2,"New line item: Other Grant (Fund 101)",grant_or_intergovernmental_revenue,medium,low,'
        '"Needs explanation.","document=doc; page=24",'
        '"Please provide the grant award letter, grant budget, match requirements, approved spending plan, and reporting requirements.",machine_generated\n'
        + 'nhr-1,"Material change: Something (Fund 101)",needs_human_review,low,low,'
        '"Needs explanation.","document=doc; page=23","What explains this?",machine_generated\n',
        encoding="utf-8",
    )

    section = render_public_records_section(findings_path)

    # Deduped: the identical grant question appears once even though two
    # findings share it.
    assert section.count("Please provide the grant award letter") == 1
    assert "What explains this?" in section
    assert not BANNED_WORDS.search(section)


def test_render_high_impact_data_quality_section_filters_by_score(tmp_path: Path) -> None:
    data_quality_path = tmp_path / "data_quality.csv"
    data_quality_path.write_text(
        DATA_QUALITY_HEADER
        + 'dq-1,unparsed_amount,high,high,"Needs verification.","document=doc; page=23",'
        "needs_manual_verification,doc,23,101,316,,50\n"
        + 'dq-2,placeholder_amount,low,medium,"Placeholder value.","document=doc; page=40",'
        "needs_manual_verification,doc,40,101,435,1,10\n",
        encoding="utf-8",
    )

    section = render_high_impact_data_quality_section(data_quality_path)

    assert "## High-impact data-quality warnings" in section
    assert "unparsed_amount" in section
    assert "Placeholder value" not in section
    assert "1 of 2" in section
    assert not BANNED_WORDS.search(section)


def test_render_appendix_data_quality_lists_everything(tmp_path: Path) -> None:
    data_quality_path = tmp_path / "data_quality.csv"
    data_quality_path.write_text(
        DATA_QUALITY_HEADER
        + 'dq-1,unparsed_amount,high,high,"Needs verification.","document=doc; page=23",'
        "needs_manual_verification,doc,23,101,316,,50\n"
        + 'dq-2,placeholder_amount,low,medium,"Placeholder value.","document=doc; page=40",'
        "needs_manual_verification,doc,40,101,435,1,10\n",
        encoding="utf-8",
    )

    section = render_appendix_data_quality(data_quality_path)

    assert "## Appendix B" in section
    assert "unparsed_amount" in section
    assert "placeholder_amount" in section


def test_render_top_absolute_and_percentage_changes(tmp_path: Path) -> None:
    top_changes_path = tmp_path / "top_changes.csv"
    top_changes_path.write_text(
        "rank_type,rank,document_id,page_number,fund_number,fund_name,budget_side,department,"
        "account,label,old_value,new_value,absolute_delta,percent_delta,status,evidence\n"
        "absolute,1,doc,23,101,General,expenditure,,40110,Big Increase,10000,20000,10000,100,present,"
        "\"document=doc; page=23\"\n"
        "percent,1,doc,23,101,General,expenditure,,40110,Big Increase,10000,20000,10000,100,present,"
        "\"document=doc; page=23\"\n",
        encoding="utf-8",
    )

    absolute_section = render_top_absolute_changes_section(top_changes_path)
    percent_section = render_top_percentage_changes_section(top_changes_path)

    assert "## Top absolute-dollar changes" in absolute_section
    assert "Big Increase" in absolute_section
    assert "## Top percentage changes" in percent_section
    assert "Big Increase" in percent_section
    assert not BANNED_WORDS.search(absolute_section)
    assert not BANNED_WORDS.search(percent_section)


def test_render_report_summary_verbosity_omits_detail(tmp_path: Path) -> None:
    findings_path = tmp_path / "findings.csv"
    findings_path.write_text(FINDINGS_HEADER, encoding="utf-8")

    out_path = tmp_path / "report.md"
    summaries = [
        {
            "fund_number": "101",
            "fund_name": "General",
            "revenue": "14057984",
            "expenditure": "14062391",
            "net": "-4407",
            "status": "extracted_with_gap",
            "revenue_line_items": "14057984",
            "transfer_in": "0",
            "expenditure_line_items": "14062391",
            "transfer_out": "0",
            "unparsed_amounts": "0",
        }
    ]

    render_report(findings_path, summaries, out_path, verbosity="summary")

    content = out_path.read_text(encoding="utf-8")
    assert "## Scope and limitations" in content
    assert "## Reconciliation summary" in content
    assert "## Executive summary" in content
    assert "## Priority follow-up areas" in content
    assert "## Top clusters" not in content
    assert "## Findings by category" not in content
    assert "## Appendix A" not in content
    assert not BANNED_WORDS.search(content)


def test_render_report_standard_verbosity_omits_appendices(tmp_path: Path) -> None:
    findings_path = tmp_path / "findings.csv"
    findings_path.write_text(FINDINGS_HEADER, encoding="utf-8")

    out_path = tmp_path / "report.md"
    summaries = [
        {
            "fund_number": "101",
            "fund_name": "General",
            "revenue": "14057984",
            "expenditure": "14062391",
            "net": "-4407",
            "status": "extracted_with_gap",
            "revenue_line_items": "14057984",
            "transfer_in": "0",
            "expenditure_line_items": "14062391",
            "transfer_out": "0",
            "unparsed_amounts": "0",
        }
    ]

    render_report(findings_path, summaries, out_path, verbosity="standard")

    content = out_path.read_text(encoding="utf-8")
    assert "## Top clusters" in content
    assert "## Findings by category" in content
    assert "## Appendix A" not in content
    assert "## Appendix D" not in content
    assert not BANNED_WORDS.search(content)


def test_render_report_full_verbosity_includes_appendices(tmp_path: Path) -> None:
    findings_path = tmp_path / "findings.csv"
    findings_path.write_text(
        FINDINGS_HEADER
        + 'reconcile-101,"Fund 101 does not reconcile in this extraction",reconciliation,low,medium,'
        '"Fund 101 General shows a net difference in this OCR-derived extraction; this does not reconcile in this extraction.",'
        '"reconciliation_file=reconcile_fund_101.csv",'
        '"Does the source document itself balance?",machine_generated\n',
        encoding="utf-8",
    )

    out_path = tmp_path / "report.md"
    summaries = [
        {
            "fund_number": "101",
            "fund_name": "General",
            "revenue": "14057984",
            "expenditure": "14062391",
            "net": "-4407",
            "status": "extracted_with_gap",
            "revenue_line_items": "14057984",
            "transfer_in": "0",
            "expenditure_line_items": "14062391",
            "transfer_out": "0",
            "unparsed_amounts": "0",
        }
    ]

    render_report(findings_path, summaries, out_path, verbosity="full")

    content = out_path.read_text(encoding="utf-8")
    assert "## Appendix A" in content
    assert "## Appendix B" in content
    assert "## Appendix C" in content
    assert "## Appendix D" in content
    assert "## How to read this report" in content
    assert not BANNED_WORDS.search(content)
