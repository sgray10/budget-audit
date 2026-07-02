from pathlib import Path

import pytest

from budget_audit.consolidate import consolidate_reviewed_rows


def test_consolidate_reviewed_rows_concatenates(tmp_path: Path) -> None:
    first = tmp_path / "first.csv"
    second = tmp_path / "second.csv"
    out_path = tmp_path / "out.csv"

    first.write_text("fund_number,label\n101,Current Tax\n101,Supplies\n", encoding="utf-8")
    second.write_text("fund_number,label\n141,Textbooks\n", encoding="utf-8")

    count = consolidate_reviewed_rows([first, second], out_path)

    assert count == 3
    lines = out_path.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "fund_number,label"
    assert lines[1:] == ["101,Current Tax", "101,Supplies", "141,Textbooks"]


def test_consolidate_reviewed_rows_header_mismatch_raises(tmp_path: Path) -> None:
    first = tmp_path / "first.csv"
    second = tmp_path / "second.csv"
    out_path = tmp_path / "out.csv"

    first.write_text("fund_number,label\n101,Current Tax\n", encoding="utf-8")
    second.write_text("fund_number,label,extra\n141,Textbooks,x\n", encoding="utf-8")

    with pytest.raises(ValueError, match="header does not match"):
        consolidate_reviewed_rows([first, second], out_path)


def test_consolidate_reviewed_rows_empty_list_raises(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="no input paths"):
        consolidate_reviewed_rows([], tmp_path / "out.csv")
