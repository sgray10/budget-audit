from __future__ import annotations

import csv
from datetime import date
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from budget_audit.enrich import enrich_ocr_rows_with_page_review
from budget_audit.extract import extract_tables, inspect_pdf, sha256_file
from budget_audit.ocr import ocr_rendered_pages
from budget_audit.ocr_reports import find_compensation_hits
from budget_audit.ocr_table_rows import extract_ocr_table_rows
from budget_audit.render import parse_page_spec, render_pdf_pages
from budget_audit.row_classify import classify_ocr_rows

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
@click.option("--document-id", default=None, help="Stable local document id. Defaults to file stem.")
@click.option("--title", default=None, help="Human-readable document title. Defaults to file stem.")
@click.option("--jurisdiction", default="", help="Jurisdiction, for example 'Weakley County, TN'.")
@click.option("--body", default="", help="Public body, committee, or department.")
@click.option("--meeting-date", default=None, help="Meeting date in YYYY-MM-DD format, if applicable.")
@click.option("--fiscal-year", default="", help="Fiscal year label, if applicable.")
@click.option("--source-url", default="", help="Public source URL, if available.")
@click.option(
    "--documents-out",
    type=click.Path(path_type=Path),
    default=None,
    help="Optional CSV path for document-level inventory output.",
)
@click.option(
    "--pages-out",
    type=click.Path(path_type=Path),
    default=None,
    help="Optional CSV path for page-level inventory output.",
)
def inspect_pdf_cmd(
    pdf_path: Path,
    document_id: str | None,
    title: str | None,
    jurisdiction: str,
    body: str,
    meeting_date: str | None,
    fiscal_year: str,
    source_url: str,
    documents_out: Path | None,
    pages_out: Path | None,
) -> None:
    """Inspect a PDF for text layers and likely tables."""
    document_id = document_id or pdf_path.stem
    title = title or pdf_path.stem
    inspections = inspect_pdf(pdf_path)
    file_hash = sha256_file(pdf_path)

    if meeting_date is not None:
        # Validate early so bad metadata does not enter inventory CSVs.
        date.fromisoformat(meeting_date)

    table = Table(title=str(pdf_path))
    table.add_column("Page", justify="right")
    table.add_column("Text Layer")
    table.add_column("Chars", justify="right")
    table.add_column("Likely Table")

    for page in inspections:
        table.add_row(
            str(page.page_number),
            "yes" if page.has_text_layer else "no",
            str(page.text_char_count),
            "yes" if page.likely_table else "no",
        )
    console.print(table)

    if documents_out is not None:
        documents_out.parent.mkdir(parents=True, exist_ok=True)
        with documents_out.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=[
                    "document_id",
                    "title",
                    "jurisdiction",
                    "body",
                    "meeting_date",
                    "fiscal_year",
                    "source_url",
                    "file_path",
                    "sha256",
                    "page_count",
                ],
            )
            writer.writeheader()
            writer.writerow(
                {
                    "document_id": document_id,
                    "title": title,
                    "jurisdiction": jurisdiction,
                    "body": body,
                    "meeting_date": meeting_date or "",
                    "fiscal_year": fiscal_year,
                    "source_url": source_url,
                    "file_path": str(pdf_path),
                    "sha256": file_hash,
                    "page_count": len(inspections),
                }
            )
        console.print(f"wrote {documents_out}")

    if pages_out is not None:
        pages_out.parent.mkdir(parents=True, exist_ok=True)
        with pages_out.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=[
                    "document_id",
                    "page_number",
                    "has_text_layer",
                    "text_char_count",
                    "likely_table",
                    "ocr_required",
                    "extraction_status",
                ],
            )
            writer.writeheader()
            for page in inspections:
                writer.writerow(
                    {
                        "document_id": document_id,
                        "page_number": page.page_number,
                        "has_text_layer": page.has_text_layer,
                        "text_char_count": page.text_char_count,
                        "likely_table": page.likely_table,
                        "ocr_required": not page.has_text_layer,
                        "extraction_status": "pending",
                    }
                )
        console.print(f"wrote {pages_out}")


@main.command("extract-tables")
@click.argument("pdf_path", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--out", "out_dir", type=click.Path(path_type=Path), required=True)
def extract_tables_cmd(pdf_path: Path, out_dir: Path) -> None:
    """Extract PDF tables to CSV files."""
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


@main.command("render-pages")
@click.argument("pdf_path", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--pages", "page_spec", required=True, help="Pages to render, e.g. '3,6-12,23'.")
@click.option("--out", "out_dir", type=click.Path(path_type=Path), required=True)
@click.option("--dpi", default=200, show_default=True, type=int)
def render_pages_cmd(pdf_path: Path, page_spec: str, out_dir: Path, dpi: int) -> None:
    """Render selected PDF pages to PNG files for visual review or OCR."""
    pages = parse_page_spec(page_spec)
    rendered = render_pdf_pages(pdf_path, out_dir, pages, dpi=dpi)

    for page in rendered:
        console.print(f"rendered page {page.page_number} -> {page.image_path}")
    console.print(f"rendered {len(rendered)} pages")



@main.command("ocr-pages")
@click.argument("rendered_dir", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--pages", "page_spec", required=True, help="Pages to OCR, e.g. '23,44-50'.")
@click.option("--out", "out_dir", type=click.Path(path_type=Path), required=True)
def ocr_pages_cmd(rendered_dir: Path, page_spec: str, out_dir: Path) -> None:
    """OCR selected rendered page images to text files."""
    pages = parse_page_spec(page_spec)
    results = ocr_rendered_pages(rendered_dir, out_dir, pages)

    for result in results:
        console.print(
            f"ocr page {result.page_number} -> {result.text_path} "
            f"({result.text_char_count} chars)"
        )
    console.print(f"ocr'd {len(results)} pages")



@main.command("find-compensation")
@click.argument("ocr_dir", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--out", "out_path", type=click.Path(path_type=Path), required=True)
@click.option("--document-id", required=True)
def find_compensation_cmd(ocr_dir: Path, out_path: Path, document_id: str) -> None:
    """Find compensation-related OCR lines and write a CSV report."""
    count = find_compensation_hits(ocr_dir, out_path, document_id)
    console.print(f"wrote {out_path} ({count} rows)")



@main.command("extract-ocr-rows")
@click.argument("ocr_dir", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--out", "out_path", type=click.Path(path_type=Path), required=True)
@click.option("--document-id", required=True)
def extract_ocr_rows_cmd(ocr_dir: Path, out_path: Path, document_id: str) -> None:
    """Extract likely budget table rows from OCR text files."""
    count = extract_ocr_table_rows(ocr_dir, out_path, document_id)
    console.print(f"wrote {out_path} ({count} rows)")



@main.command("enrich-ocr-rows")
@click.argument("rows_path", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option(
    "--page-review",
    "page_review_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    required=True,
)
@click.option("--out", "out_path", type=click.Path(path_type=Path), required=True)
def enrich_ocr_rows_cmd(rows_path: Path, page_review_path: Path, out_path: Path) -> None:
    """Enrich extracted OCR rows with page-review metadata."""
    count = enrich_ocr_rows_with_page_review(rows_path, page_review_path, out_path)
    console.print(f"wrote {out_path} ({count} rows)")



@main.command("classify-ocr-rows")
@click.argument("rows_path", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--out", "out_path", type=click.Path(path_type=Path), required=True)
def classify_ocr_rows_cmd(rows_path: Path, out_path: Path) -> None:
    """Classify extracted/enriched OCR rows by row type and category."""
    count = classify_ocr_rows(rows_path, out_path)
    console.print(f"wrote {out_path} ({count} rows)")



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
