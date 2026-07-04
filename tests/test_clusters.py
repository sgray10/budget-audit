import csv
from pathlib import Path

from budget_audit.clusters import build_clusters, cluster_id_for, extract_label_prefix

ROW_HEADER = (
    "document_id,page_number,row_type,fund_number,fund_name,section_hint,account,label,budget_26_27\n"
)


def test_extract_label_prefix_matches_real_patterns() -> None:
    assert extract_label_prefix("OPID Opioid Settlement Funds") == "OPID"
    assert extract_label_prefix("BONUS Social Security") == "BONUS"
    assert extract_label_prefix("+ISM State Retirement") == "+ISM"
    assert extract_label_prefix("=ITG Social Security") == "=ITG"


def test_extract_label_prefix_no_match() -> None:
    assert extract_label_prefix("Current Tax") is None
    assert extract_label_prefix("Office Supplies") is None


def test_cluster_id_for() -> None:
    assert cluster_id_for("101", "OPID") == "101-OPID"


def test_build_clusters_detects_paired_revenue_expense(tmp_path: Path) -> None:
    rows_path = tmp_path / "rows.csv"
    out_path = tmp_path / "clusters.csv"

    # Mirrors the real OPID (Opioid Settlement) case: a revenue line and
    # several expenditure allocations sharing the OPID prefix.
    rows_path.write_text(
        ROW_HEADER
        + "doc,25,line_item,101,General,Fund 101 General Fund revenues,36900,OPID Opioid Settlement Funds,50000\n"
        + "doc,60,line_item,101,General,Fund 101 General Fund expenditures,510,OPID City of Dresden,10000\n"
        + "doc,60,line_item,101,General,Fund 101 General Fund expenditures,510,OPID City of Martin,17000\n",
        encoding="utf-8",
    )

    stats = build_clusters(rows_path, out_path)

    assert stats["clusters"] == 1
    assert stats["paired_clusters"] == 1
    assert stats["unclustered_line_items"] == 0

    rows = list(csv.DictReader(out_path.open(encoding="utf-8")))
    assert len(rows) == 1
    assert rows[0]["cluster_id"] == "101-OPID"
    assert rows[0]["revenue_total"] == "50000"
    assert rows[0]["expenditure_total"] == "27000"
    assert rows[0]["is_paired"] == "true"
    assert rows[0]["line_item_count"] == "3"


def test_build_clusters_single_sided_is_not_paired(tmp_path: Path) -> None:
    rows_path = tmp_path / "rows.csv"
    out_path = tmp_path / "clusters.csv"

    rows_path.write_text(
        ROW_HEADER
        + "doc,60,line_item,101,General,Fund 101 General Fund expenditures,201,BONUS Social Security,5000\n",
        encoding="utf-8",
    )

    build_clusters(rows_path, out_path)

    rows = list(csv.DictReader(out_path.open(encoding="utf-8")))
    assert rows[0]["is_paired"] == "false"
    assert rows[0]["revenue_total"] == "0"
    assert rows[0]["expenditure_total"] == "5000"


def test_build_clusters_ignores_non_line_item_rows_and_unclustered_labels(tmp_path: Path) -> None:
    rows_path = tmp_path / "rows.csv"
    out_path = tmp_path / "clusters.csv"

    rows_path.write_text(
        ROW_HEADER
        + "doc,60,total,101,General,Fund 101 General Fund expenditures,,Sub-Total,5000\n"
        + "doc,61,line_item,101,General,Fund 101 General Fund expenditures,435,Office Supplies,1000\n",
        encoding="utf-8",
    )

    stats = build_clusters(rows_path, out_path)

    assert stats["clusters"] == 0
    assert stats["unclustered_line_items"] == 1


def test_build_clusters_tags_debt_service_cluster_type(tmp_path: Path) -> None:
    rows_path = tmp_path / "rows.csv"
    out_path = tmp_path / "clusters.csv"

    # Real Fund 151 pattern: principal and interest lines sharing a debt
    # prefix, no offsetting revenue.
    rows_path.write_text(
        ROW_HEADER
        + "doc,145,line_item,151,Debt Service,Fund 151 Debt Service expenditures,602,JAIL Principal on Notes,470000\n"
        + "doc,146,line_item,151,Debt Service,Fund 151 Debt Service expenditures,613,JAIL Interest on Other Loans Payable,89219\n",
        encoding="utf-8",
    )

    build_clusters(rows_path, out_path)

    rows = list(csv.DictReader(out_path.open(encoding="utf-8")))
    assert rows[0]["cluster_type"] == "debt_service"
    assert "debt-service" in rows[0]["narrative"]


def test_build_clusters_tags_allocation_program_cluster_type(tmp_path: Path) -> None:
    rows_path = tmp_path / "rows.csv"
    out_path = tmp_path / "clusters.csv"

    # Real Fund 101 OPID pattern: opioid settlement revenue (grant-like)
    # paired with several named-recipient expenditure lines (account 316).
    # Recipient allocation should win over the grant-revenue signal as the
    # cluster's type, since "who is the money going to" matters more here.
    rows_path.write_text(
        ROW_HEADER
        + "doc,25,line_item,101,General,Fund 101 General Fund revenues,46845,OPID Opioid Settlement Funds,50000\n"
        + "doc,60,line_item,101,General,Fund 101 General Fund expenditures,316,OPID City of Dresden,10000\n"
        + "doc,60,line_item,101,General,Fund 101 General Fund expenditures,316,OPID City of Martin,17000\n",
        encoding="utf-8",
    )

    build_clusters(rows_path, out_path)

    rows = list(csv.DictReader(out_path.open(encoding="utf-8")))
    assert rows[0]["cluster_type"] == "allocation_program"
    assert "named external recipients" in rows[0]["narrative"]


def test_build_clusters_tags_grant_funded_capital_project_cluster_type(tmp_path: Path) -> None:
    rows_path = tmp_path / "rows.csv"
    out_path = tmp_path / "clusters.csv"

    # Real Fund 101 CRD pattern: a state grant revenue line paired with a
    # building-improvements expenditure line under the same prefix.
    rows_path.write_text(
        ROW_HEADER
        + "doc,30,line_item,101,General,Fund 101 General Fund revenues,46980,CRD Other State Grants,500000\n"
        + "doc,70,line_item,101,General,Fund 101 General Fund expenditures,707,CRD Building Improvements,550000\n",
        encoding="utf-8",
    )

    build_clusters(rows_path, out_path)

    rows = list(csv.DictReader(out_path.open(encoding="utf-8")))
    assert rows[0]["cluster_type"] == "grant_funded_capital_project"
    assert "grant/construction project" in rows[0]["narrative"]


def test_build_clusters_tags_grant_funded_program_when_no_capital_side(tmp_path: Path) -> None:
    rows_path = tmp_path / "rows.csv"
    out_path = tmp_path / "clusters.csv"

    # Real Fund 141 ABE pattern: grant revenue paired with personnel/benefits
    # expenditure, not capital -- a program, not a construction project.
    rows_path.write_text(
        ROW_HEADER
        + "doc,87,line_item,141,General Purpose School,Fund 141 General Purpose School revenues,46590,ABE Adult Basic Education (ABE),100000\n"
        + "doc,105,line_item,141,General Purpose School,Fund 141 General Purpose School expenditures - Instruction,207,ABE Medical Insurance,8000\n"
        + "doc,116,line_item,141,General Purpose School,Fund 141 General Purpose School expenditures - Instruction,212,ABE Medicare Liability,1500\n",
        encoding="utf-8",
    )

    build_clusters(rows_path, out_path)

    rows = list(csv.DictReader(out_path.open(encoding="utf-8")))
    assert rows[0]["cluster_type"] == "grant_funded_program"
    assert "grant- or program-funded activity" in rows[0]["narrative"]


def test_build_clusters_tags_mixed_grant_program_when_capital_share_is_intermediate(tmp_path: Path) -> None:
    rows_path = tmp_path / "rows.csv"
    out_path = tmp_path / "clusters.csv"

    # Real Fund 141 ISM pattern: grant revenue paired with an expense side
    # that is substantially capital (equipment/building) but also carries
    # real personnel/benefits spending -- ~73% capital in the real data,
    # between the configured dominant (80%) and immaterial (20%) thresholds.
    rows_path.write_text(
        ROW_HEADER
        + "doc,87,line_item,141,General Purpose School,Fund 141 General Purpose School revenues,46790,ISM Innovative Schools Model (ISM),421711\n"
        + "doc,120,line_item,141,General Purpose School,Fund 141 General Purpose School expenditures,730,ISM Vocational Instructional Equipment,152706\n"
        + "doc,121,line_item,141,General Purpose School,Fund 141 General Purpose School expenditures,707,ISM Building Improvements,146947\n"
        + "doc,105,line_item,141,General Purpose School,Fund 141 General Purpose School expenditures,116,ISM Teachers,70433\n"
        + "doc,105,line_item,141,General Purpose School,Fund 141 General Purpose School expenditures,207,ISM Medical Insurance,9000\n",
        encoding="utf-8",
    )

    build_clusters(rows_path, out_path)

    rows = list(csv.DictReader(out_path.open(encoding="utf-8")))
    assert rows[0]["cluster_type"] == "mixed_grant_program"
    assert "mix of program costs" in rows[0]["narrative"]
    # Capital share must be tracked for the threshold decision.
    assert rows[0]["capital_expenditure_total"] == "299653"


def test_build_clusters_capital_project_requires_capital_dominance(tmp_path: Path) -> None:
    rows_path = tmp_path / "rows.csv"
    out_path = tmp_path / "clusters.csv"

    # A paired grant cluster whose expense side is almost all personnel with
    # a token equipment line must NOT be called a capital project.
    rows_path.write_text(
        ROW_HEADER
        + "doc,87,line_item,141,General Purpose School,Fund 141 General Purpose School revenues,46590,SUM Summer Learning Camp,480962\n"
        + "doc,110,line_item,141,General Purpose School,Fund 141 General Purpose School expenditures,116,SUM Teachers,430000\n"
        + "doc,111,line_item,141,General Purpose School,Fund 141 General Purpose School expenditures,790,SUM Other Equipment,48912\n",
        encoding="utf-8",
    )

    build_clusters(rows_path, out_path)

    rows = list(csv.DictReader(out_path.open(encoding="utf-8")))
    # ~10% capital share -> below the immaterial threshold -> plain program.
    assert rows[0]["cluster_type"] == "grant_funded_program"


def test_build_clusters_one_sided_narrative_includes_note(tmp_path: Path) -> None:
    from budget_audit.clusters import ONE_SIDED_NOTE

    rows_path = tmp_path / "rows.csv"
    out_path = tmp_path / "clusters.csv"

    # Real Fund 151 JAIL pattern: debt-service expenditure with no offsetting
    # revenue inside the extracted pages.
    rows_path.write_text(
        ROW_HEADER
        + "doc,145,line_item,151,Debt Service,Fund 151 Debt Service expenditures,602,JAIL Principal on Notes,470000\n"
        + "doc,146,line_item,151,Debt Service,Fund 151 Debt Service expenditures,613,JAIL Interest on Other Loans Payable,89219\n",
        encoding="utf-8",
    )

    build_clusters(rows_path, out_path)

    rows = list(csv.DictReader(out_path.open(encoding="utf-8")))
    assert rows[0]["is_paired"] == "false"
    assert ONE_SIDED_NOTE in rows[0]["narrative"]


def test_build_clusters_records_key_line_references(tmp_path: Path) -> None:
    rows_path = tmp_path / "rows.csv"
    out_path = tmp_path / "clusters.csv"

    rows_path.write_text(
        ROW_HEADER
        + "doc,30,line_item,101,General,Fund 101 General Fund revenues,46980,CRD Other State Grants,500000\n"
        + "doc,70,line_item,101,General,Fund 101 General Fund expenditures,707,CRD Building Improvements,550000\n",
        encoding="utf-8",
    )

    build_clusters(rows_path, out_path)

    rows = list(csv.DictReader(out_path.open(encoding="utf-8")))
    assert "page=30" in rows[0]["key_revenue_line"]
    assert "account=46980" in rows[0]["key_revenue_line"]
    assert "page=70" in rows[0]["key_expenditure_line"]
    assert "CRD Building Improvements" in rows[0]["key_expenditure_line"]
