from __future__ import annotations

import csv
from pathlib import Path


def consolidate_reviewed_rows(
    input_paths: list[Path],
    out_path: Path,
) -> int:
    """Concatenate reviewed/corrected row CSVs covering disjoint page ranges
    into one canonical multi-fund dataset.

    Input files are expected to cover disjoint page ranges (e.g. one range
    per checkpoint), so this is plain concatenation with no dedup. All inputs
    must share the same header; a mismatch means the schema drifted between
    pipeline runs and should be caught here rather than silently merged.
    """
    if not input_paths:
        raise ValueError("no input paths provided")

    fieldnames: list[str] | None = None
    all_rows: list[dict[str, str]] = []

    for path in input_paths:
        reader = csv.DictReader(path.open(encoding="utf-8"))
        rows = list(reader)
        row_fieldnames = list(reader.fieldnames) if reader.fieldnames is not None else None
        if fieldnames is None:
            fieldnames = row_fieldnames
        elif row_fieldnames != fieldnames:
            raise ValueError(f"{path} header does not match {input_paths[0]} header")
        all_rows.extend(rows)

    if fieldnames is None:
        raise ValueError("no rows found across input paths")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)

    return len(all_rows)
