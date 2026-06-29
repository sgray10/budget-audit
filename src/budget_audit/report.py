from __future__ import annotations

from decimal import Decimal


def format_money(value: Decimal | None) -> str:
    if value is None:
        return ""
    return f"${value:,.2f}"


def markdown_table(headers: list[str], rows: list[list[str]]) -> str:
    """Render a simple markdown table."""
    out = ["| " + " | ".join(headers) + " |"]
    out.append("| " + " | ".join("---" for _ in headers) + " |")
    for row in rows:
        out.append("| " + " | ".join(row) + " |")
    return "\n".join(out)
