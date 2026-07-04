from pathlib import Path

from budget_audit.related_items import (
    LabelIndexEntry,
    build_label_index,
    distinctive_keywords,
    related_for_fund_name,
    related_for_keywords,
    related_for_prefix,
)

ROW_HEADER = "document_id,page_number,row_type,fund_number,fund_name,account,label\n"


def _index(tmp_path: Path, rows: str) -> list[LabelIndexEntry]:
    rows_path = tmp_path / "rows.csv"
    rows_path.write_text(ROW_HEADER + rows, encoding="utf-8")
    return build_label_index(rows_path)


def test_fund_name_links_nursing_home_zero_out_to_fund_101_nh_lines(tmp_path: Path) -> None:
    # The real motivating case: Fund 202's whole-fund zero-out should surface
    # Fund 101's NH revenue lines, which mention the fund by name.
    index = _index(
        tmp_path,
        "doc,24,line_item,101,General,44110,NH Investment Income - Nursing Home Funds\n"
        "doc,27,line_item,101,General,48130,NH Contributions - Nursing Home\n"
        "doc,156,line_item,202,Nursing Home,43120,Patient Charges\n"
        "doc,30,line_item,101,General,435,Office Supplies\n",
    )

    related = related_for_fund_name("202", "Nursing Home", index)

    descriptions = [item.description for item in related]
    assert len(related) == 2
    assert any("NH Investment Income - Nursing Home Funds" in d for d in descriptions)
    assert any("NH Contributions - Nursing Home" in d for d in descriptions)
    # Rows in the fund itself are not "related items" -- they ARE the fund.
    assert not any("Patient Charges" in d for d in descriptions)


def test_prefix_similarity_links_opid_to_opia() -> None:
    cluster_rows = [
        {
            "cluster_id": "101-OPIA",
            "fund_number": "101",
            "prefix": "OPIA",
            "sample_labels": "OPIA Opioid Settlement Funds - Past Remediation",
        },
        {
            "cluster_id": "151-JAIL",
            "fund_number": "151",
            "prefix": "JAIL",
            "sample_labels": "JAIL Principal on Notes",
        },
    ]

    related = related_for_prefix("101", "OPID", cluster_rows)

    assert len(related) == 1
    assert "101-OPIA" in related[0].description
    assert related[0].reason == "prefix"


def test_keyword_linking_requires_rare_keyword(tmp_path: Path) -> None:
    # "Building" appears everywhere in budget labels; it must not link two
    # unrelated rows. A packet-rare word ("Broadband") may.
    common = "".join(
        f"doc,{30 + i},line_item,101,General,335,Maintenance/Repair - Building {i}\n" for i in range(6)
    )
    index = _index(
        tmp_path,
        common
        + "doc,66,line_item,101,General,316,BRC Broadband Ready Communities\n"
        + "doc,153,line_item,172,Community Development,46980,Broadband Communities Facilities Grant\n",
    )

    via_common = related_for_keywords(["Building Construction"], "172", "", index)
    via_rare = related_for_keywords(["Broadband Communities Facilities Grant"], "172", "", index)

    assert via_common == []
    assert any("BRC Broadband Ready Communities" in item.description for item in via_rare)


def test_recipient_phrases_do_not_leak_keywords() -> None:
    # "City of Dresden" names a recipient, not a program -- "Dresden" must
    # not become a linking keyword.
    keywords = distinctive_keywords(["OPID City of Dresden", "OPID Opioid Settlement Funds"])

    assert "Dresden" not in keywords
    assert "Opioid" in keywords
