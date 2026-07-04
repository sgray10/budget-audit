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
