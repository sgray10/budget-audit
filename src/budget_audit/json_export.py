from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


def csv_to_json(csv_path: Path, json_path: Path) -> int:
    """Dump a CSV's rows as a JSON array of objects, for machine-readable
    consumption alongside the CSV. The CSV remains the canonical structured
    output; this is a sibling format, not a separate source of truth.
    """
    rows = list(csv.DictReader(csv_path.open(encoding="utf-8")))
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    return len(rows)


def write_json(data: Any, json_path: Path) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")


__all__ = ["csv_to_json", "write_json"]
