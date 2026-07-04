import re
from pathlib import Path

from decimal import Decimal

from budget_audit.report import (
    format_money,
    load_reconcile_summary,
    markdown_table,
    render_data_quality_section,
    render_findings_section,
    render_report,
    render_scope_section,
)

BANNED_WORDS = re.compile(r"\bhidden\b|\bsuspicious\b|\bwrong\b", re.IGNORECASE)

FINDINGS_HEADER = "finding_id,title,category,severity,confidence,summary,evidence,open_questions,status\n"


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
    assert "not yet included" not in section


def test_load_reconcile_summary(tmp_path: Path) -> None:
    path = tmp_path / "reconcile_101.csv"
    path.write_text(
        "metric,value\nrevenue_with_transfers,14057984\nexpenditure_with_transfers,14062391\nnet_with_transfers,-4407\n",
        encoding="utf-8",
    )

    summary = load_reconcile_summary("101", path)

    assert summary["fund_number"] == "101"
    assert summary["fund_name"] == "General"
    assert summary["revenue"] == "14057984"
    assert summary["expenditure"] == "14062391"
    assert summary["net"] == "-4407"


def test_render_findings_section_uses_neutral_language(tmp_path: Path) -> None:
    findings_path = tmp_path / "findings.csv"
    findings_path.write_text(
        FINDINGS_HEADER
        + 'delta-1,"Material change: Big Increase (Fund 101)",delta,low,low,'
        '"This change is above the configured materiality threshold and needs explanation.",'
        '"document=doc; page=23","What explains this?",draft\n',
        encoding="utf-8",
    )

    section = render_findings_section(findings_path)

    assert "Material year-over-year changes" in section
    assert not BANNED_WORDS.search(section)


def test_render_data_quality_section_lists_warnings(tmp_path: Path) -> None:
    data_quality_path = tmp_path / "data_quality.csv"
    data_quality_path.write_text(
        "warning_id,warning_type,severity,confidence,summary,evidence,status\n"
        'dq-1,unparsed_amount,high,high,"The amount needs verification.",'
        '"document=doc; page=23",needs_manual_verification\n',
        encoding="utf-8",
    )

    section = render_data_quality_section(data_quality_path)

    assert "## Data-quality warnings" in section
    assert "unparsed_amount" in section
    assert "needs verification" in section
    assert not BANNED_WORDS.search(section)


def test_render_report_writes_expected_sections(tmp_path: Path) -> None:
    findings_path = tmp_path / "findings.csv"
    findings_path.write_text(
        FINDINGS_HEADER
        + 'reconcile-101,"Fund 101 does not reconcile in this extraction",reconciliation,low,medium,'
        '"Fund 101 General shows a net difference in this OCR-derived extraction; this does not reconcile in this extraction.",'
        '"reconciliation_file=reconcile_fund_101.csv",'
        '"Does the source document itself balance?",draft\n',
        encoding="utf-8",
    )

    out_path = tmp_path / "report.md"
    summaries = [
        {"fund_number": "101", "fund_name": "General", "revenue": "14057984", "expenditure": "14062391", "net": "-4407"}
    ]

    render_report(findings_path, summaries, out_path)

    content = out_path.read_text(encoding="utf-8")
    assert "## Scope" in content
    assert "## Reconciliation summary" in content
    assert "## Data-quality warnings" in content
    assert "## Findings" in content
    assert "## How to read this report" in content
    assert not BANNED_WORDS.search(content)
