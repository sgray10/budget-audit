from __future__ import annotations

from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from budget_audit.extract import extract_tables, inspect_pdf

console = Console()


@click.group()
def main() -> None:
    """Budget Audit command line tools."""


@main.command("init-project")
@click.argument("path", type=click.Path(path_type=Path))
def init_project(path: Path) -> None:
    """Create a local data/report directory structure."""
    for child in ["data/raw", "data/interim", "data/processed", "reports"]:
        directory = path / child
        directory.mkdir(parents=True, exist_ok=True)
        console.print(f"created {directory}")


@main.command("inspect-pdf")
@click.argument("pdf_path", type=click.Path(exists=True, dir_okay=False, path_type=Path))
def inspect_pdf_cmd(pdf_path: Path) -> None:
    """Inspect a PDF for text layers and likely tables."""
    table = Table(title=str(pdf_path))
    table.add_column("Page", justify="right")
    table.add_column("Text Layer")
    table.add_column("Chars", justify="right")
    table.add_column("Likely Table")

    for page in inspect_pdf(pdf_path):
        table.add_row(
            str(page.page_number),
            "yes" if page.has_text_layer else "no",
            str(page.text_char_count),
            "yes" if page.likely_table else "no",
        )
    console.print(table)


@main.command("extract-tables")
@click.argument("pdf_path", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--out", "out_dir", type=click.Path(path_type=Path), required=True)
def extract_tables_cmd(pdf_path: Path, out_dir: Path) -> None:
    """Extract PDF tables to CSV files."""
    import csv

    out_dir.mkdir(parents=True, exist_ok=True)
    tables = extract_tables(pdf_path)
    for extracted in tables:
        filename = f"page-{extracted.page_number:03d}-table-{extracted.table_index:02d}.csv"
        out_path = out_dir / filename
        with out_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerows(extracted.rows)
        console.print(f"wrote {out_path}")

    console.print(f"extracted {len(tables)} tables")


@main.command("normalize")
@click.argument("input_path", type=click.Path(exists=True, path_type=Path))
@click.option("--out", "out_path", type=click.Path(path_type=Path), required=True)
def normalize_cmd(input_path: Path, out_path: Path) -> None:
    """Placeholder for normalization pipeline."""
    console.print(f"TODO: normalize {input_path} -> {out_path}")


@main.command("reconcile")
@click.argument("input_path", type=click.Path(exists=True, path_type=Path))
def reconcile_cmd(input_path: Path) -> None:
    """Placeholder for reconciliation checks."""
    console.print(f"TODO: reconcile {input_path}")


@main.command("report")
@click.argument("input_path", type=click.Path(exists=True, path_type=Path))
@click.option("--out", "out_path", type=click.Path(path_type=Path), required=True)
def report_cmd(input_path: Path, out_path: Path) -> None:
    """Placeholder for markdown report generation."""
    console.print(f"TODO: report {input_path} -> {out_path}")


if __name__ == "__main__":
    main()
