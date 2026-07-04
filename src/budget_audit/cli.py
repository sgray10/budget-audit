from __future__ import annotations

import csv
from datetime import date
from decimal import Decimal
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from budget_audit.analyze import MaterialityThreshold, analyze_deltas
from budget_audit.clusters import build_clusters
from budget_audit.compensation import analyze_compensation
from budget_audit.consolidate import consolidate_reviewed_rows
from budget_audit.corrections import apply_row_corrections
from budget_audit.enrich import enrich_ocr_rows_with_page_review
from budget_audit.extract import extract_tables, inspect_pdf, sha256_file
from budget_audit.findings import build_findings
from budget_audit.ocr import ocr_rendered_pages
from budget_audit.ocr_reports import find_compensation_hits
from budget_audit.ocr_table_rows import extract_ocr_table_rows
from budget_audit.reconcile import reconcile_fund
from budget_audit.render import parse_page_spec, render_pdf_pages
from budget_audit.report import VERBOSITY_LEVELS, load_reconcile_summary, render_report
from budget_audit.report_workflow import run_report_workflow
from budget_audit.review import build_ocr_review_queue
from budget_audit.row_classify import classify_ocr_rows
from budget_audit.subtotal_reconcile import reconcile_subtotals
from budget_audit.summarize import summarize_classified_ocr_rows
from budget_audit.workflow import parse_fund_list, run_reviewed_range_workflow

console = Console()


def _parse_reconcile_specs(specs: tuple[str, ...]) -> dict[str, Path]:
    """Parse repeatable '--reconcile fund=path' options into a fund->path map."""
    reconcile_paths: dict[str, Path] = {}
    for spec in specs:
        fund, sep, path_str = spec.partition("=")
        if not sep:
            raise click.BadParameter(f"expected 'fund=path', got {spec!r}")
        reconcile_paths[fund.strip()] = Path(path_str)
    return reconcile_paths


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
@click.option("--pages", "page_spec", default=None, help="Optional pages to extract, e.g. '23-85'.")
@click.option("--out", "out_path", type=click.Path(path_type=Path), required=True)
@click.option("--document-id", required=True)
def extract_ocr_rows_cmd(ocr_dir: Path, page_spec: str | None, out_path: Path, document_id: str) -> None:
    """Extract likely budget table rows from OCR text files."""
    pages = set(parse_page_spec(page_spec)) if page_spec is not None else None
    count = extract_ocr_table_rows(ocr_dir, out_path, document_id, pages=pages)
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


@main.command("summarize-ocr-rows")
@click.argument("rows_path", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--out-dir", "out_dir", type=click.Path(path_type=Path), required=True)
def summarize_ocr_rows_cmd(rows_path: Path, out_dir: Path) -> None:
    """Summarize classified OCR budget rows."""
    stats = summarize_classified_ocr_rows(rows_path, out_dir)
    console.print(
        "summarized "
        f"{stats['line_rows']} line rows; "
        f"excluded {stats['non_line_rows']} non-line rows; "
        f"{stats['unparsed_amounts']} unparsed amounts"
    )
    console.print(f"wrote summaries to {out_dir}")


@main.command("review-ocr-rows")
@click.argument("rows_path", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--out", "out_path", type=click.Path(path_type=Path), required=True)
def review_ocr_rows_cmd(rows_path: Path, out_path: Path) -> None:
    """Create a review queue for suspicious OCR-derived rows."""
    count = build_ocr_review_queue(rows_path, out_path)
    console.print(f"wrote {out_path} ({count} rows)")


@main.command("apply-row-corrections")
@click.argument("rows_path", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option(
    "--corrections",
    "corrections_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    required=True,
)
@click.option("--out", "out_path", type=click.Path(path_type=Path), required=True)
@click.option(
    "--strict/--no-strict",
    default=False,
    show_default=True,
    help="Raise if any replace correction is unmatched or ambiguous, instead of warning.",
)
def apply_row_corrections_cmd(
    rows_path: Path, corrections_path: Path, out_path: Path, strict: bool
) -> None:
    """Apply manual row corrections to an extracted/classified OCR row CSV."""
    stats = apply_row_corrections(rows_path, corrections_path, out_path, strict=strict)
    console.print(
        f"wrote {out_path} "
        f"({stats['output_rows']} rows; "
        f"{stats['replaced']} replaced; "
        f"{stats['added']} added)"
    )
    if stats["unmatched_replacements"]:
        console.print(
            f"[yellow]warning: {len(stats['unmatched_replacements'])} unmatched replace correction(s)[/yellow]"
        )
        for item in stats["unmatched_replacements"]:
            console.print(f"  [yellow]unmatched:[/yellow] {item}")
    if stats["ambiguous_extracted_matches"]:
        console.print(
            f"[yellow]warning: {len(stats['ambiguous_extracted_matches'])} ambiguous extracted-row match(es)[/yellow]"
        )
        for item in stats["ambiguous_extracted_matches"]:
            console.print(f"  [yellow]ambiguous:[/yellow] {item}")
    if stats["ambiguous_correction_keys"]:
        console.print(
            f"[yellow]warning: {len(stats['ambiguous_correction_keys'])} duplicate correction key(s) (last one wins)[/yellow]"
        )
        for item in stats["ambiguous_correction_keys"]:
            console.print(f"  [yellow]duplicate:[/yellow] {item}")



@main.command("run-reviewed-range")
@click.argument("ocr_dir", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--pages", "page_spec", required=True, help="Pages to process, e.g. '23-85'.")
@click.option("--document-id", required=True)
@click.option(
    "--page-review",
    "page_review_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    required=True,
)
@click.option(
    "--corrections",
    "corrections_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=None,
)
@click.option("--out-dir", "out_dir", type=click.Path(path_type=Path), required=True)
@click.option("--funds", "fund_spec", default="", help="Comma-separated funds to reconcile, e.g. '101,116,122,131'.")
def run_reviewed_range_cmd(
    ocr_dir: Path,
    page_spec: str,
    document_id: str,
    page_review_path: Path,
    corrections_path: Path | None,
    out_dir: Path,
    fund_spec: str,
) -> None:
    """Run the reviewed OCR range workflow end to end."""
    pages = set(parse_page_spec(page_spec))
    funds = parse_fund_list(fund_spec)
    stats = run_reviewed_range_workflow(
        ocr_dir,
        page_spec=page_spec,
        pages=pages,
        document_id=document_id,
        page_review_path=page_review_path,
        corrections_path=corrections_path,
        out_dir=out_dir,
        funds=funds,
    )
    console.print(
        f"workflow complete: "
        f"{stats['raw_rows']} raw rows; "
        f"{stats['classified_rows']} classified rows; "
        f"{stats['replaced_rows']} replaced; "
        f"{stats['added_rows']} added; "
        f"{stats['review_rows']} review rows; "
        f"{stats['reconciled_funds']} funds reconciled"
    )



@main.command("normalize")
@click.argument("input_path", type=click.Path(exists=True, path_type=Path))
@click.option("--out", "out_path", type=click.Path(path_type=Path), required=True)
def normalize_cmd(input_path: Path, out_path: Path) -> None:
    """Placeholder for normalization pipeline."""
    console.print(f"TODO: normalize {input_path} -> {out_path}")


@main.command("reconcile")
@click.argument("rows_path", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--fund", "fund_number", required=True, help="Fund number to reconcile, e.g. 101.")
@click.option("--out", "out_path", type=click.Path(path_type=Path), required=True)
def reconcile_cmd(rows_path: Path, fund_number: str, out_path: Path) -> None:
    """Reconcile revenue, expenditures, and transfers for one fund."""
    stats = reconcile_fund(rows_path, out_path, fund_number)
    console.print(f"wrote {out_path}")
    console.print(
        f"fund {fund_number}: "
        f"revenue with transfers={stats['revenue_with_transfers']}; "
        f"expenditures with transfers={stats['expenditure_with_transfers']}; "
        f"net={stats['net_with_transfers']}"
    )


@main.command("reconcile-subtotals")
@click.argument("rows_path", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--out", "out_path", type=click.Path(path_type=Path), required=True)
@click.option(
    "--tolerance",
    default=0,
    show_default=True,
    type=int,
    help="Allowed absolute-dollar difference before a group is flagged as a mismatch.",
)
def reconcile_subtotals_cmd(rows_path: Path, out_path: Path, tolerance: int) -> None:
    """Compare corrected line-item subtotal groups to their source total/subtotal lines."""
    stats = reconcile_subtotals(rows_path, out_path, tolerance=Decimal(tolerance))
    console.print(
        f"wrote {out_path}: "
        f"{stats['compared']} groups compared; "
        f"{stats['matched']} matched; "
        f"{stats['mismatched']} mismatched; "
        f"{stats['skipped_zero_line_item_groups']} roll-up totals skipped"
    )


@main.command("consolidate-reviewed-rows")
@click.argument(
    "rows_paths",
    nargs=-1,
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    required=True,
)
@click.option("--out", "out_path", type=click.Path(path_type=Path), required=True)
def consolidate_reviewed_rows_cmd(rows_paths: tuple[Path, ...], out_path: Path) -> None:
    """Concatenate disjoint reviewed/corrected row CSVs into one canonical dataset."""
    count = consolidate_reviewed_rows(list(rows_paths), out_path)
    console.print(f"wrote {out_path} ({count} rows)")


@main.command("analyze-deltas")
@click.argument("rows_path", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--out-dir", "out_dir", type=click.Path(path_type=Path), required=True)
@click.option("--min-absolute", default=5000, show_default=True, type=int, help="Minimum absolute-dollar delta to flag as material.")
@click.option("--min-percent", default=15, show_default=True, type=int, help="Minimum percent delta to flag as material.")
@click.option(
    "--require-both/--either",
    "require_both",
    default=True,
    show_default=True,
    help="Require both absolute and percent thresholds to flag material, or trigger on either.",
)
def analyze_deltas_cmd(
    rows_path: Path, out_dir: Path, min_absolute: int, min_percent: int, require_both: bool
) -> None:
    """Compute year-over-year deltas per line item and flag material changes."""
    threshold = MaterialityThreshold(
        min_absolute=Decimal(min_absolute), min_percent=Decimal(min_percent), require_both=require_both
    )
    stats = analyze_deltas(rows_path, out_dir, threshold)
    console.print(
        f"analyzed {stats['line_items']} line items; "
        f"{stats['material_rows']} material transitions; "
        f"{stats['new_line_rows']} new; {stats['eliminated_line_rows']} eliminated"
    )
    console.print(f"wrote delta CSVs to {out_dir}")


@main.command("analyze-compensation")
@click.argument("rows_path", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--out-dir", "out_dir", type=click.Path(path_type=Path), required=True)
def analyze_compensation_cmd(rows_path: Path, out_dir: Path) -> None:
    """Roll up compensation-related rows and flag aggregate vs needs-review labels."""
    stats = analyze_compensation(rows_path, out_dir)
    console.print(
        f"analyzed {stats['compensation_rows']} compensation rows; "
        f"{stats['needs_review_rows']} needs_review; {stats['aggregate_rows']} aggregate"
    )
    console.print(f"wrote compensation CSVs to {out_dir}")


@main.command("build-clusters")
@click.argument("rows_path", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--out", "out_path", type=click.Path(path_type=Path), required=True)
def build_clusters_cmd(rows_path: Path, out_path: Path) -> None:
    """Group line items by fund and label prefix, flagging paired revenue/expense clusters."""
    stats = build_clusters(rows_path, out_path)
    console.print(
        f"wrote {out_path}: {stats['clusters']} clusters "
        f"({stats['paired_clusters']} paired); "
        f"{stats['unclustered_line_items']} line items had no detectable prefix"
    )


@main.command("build-findings")
@click.argument("deltas_path", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option(
    "--compensation-flags",
    "compensation_flags_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    required=True,
)
@click.option(
    "--reconcile",
    "reconcile_specs",
    multiple=True,
    required=True,
    help="fund=path pairs, e.g. --reconcile 101=data/processed/reconcile_fund_101_023_085.csv (repeatable).",
)
@click.option("--out", "out_path", type=click.Path(path_type=Path), required=True)
def build_findings_cmd(
    deltas_path: Path,
    compensation_flags_path: Path,
    reconcile_specs: tuple[str, ...],
    out_path: Path,
) -> None:
    """Assemble delta, compensation, and reconciliation findings into one findings CSV.

    Structural-change and grant/capital-pair findings are only added by the
    full generate-report workflow, which has line_item_deltas.csv already
    available to detect them from -- not by this standalone command.
    """
    reconcile_paths = _parse_reconcile_specs(reconcile_specs)
    stats = build_findings(deltas_path, compensation_flags_path, reconcile_paths, out_path)
    console.print(
        f"wrote {out_path}: {stats['delta_findings']} delta, "
        f"{stats['compensation_findings']} compensation, "
        f"{stats['reconciliation_findings']} reconciliation findings "
        f"({stats['total_findings']} total)"
    )


@main.command("report")
@click.argument("findings_path", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option(
    "--reconcile",
    "reconcile_specs",
    multiple=True,
    required=True,
    help="fund=path pairs for the reconciliation summary table, repeatable.",
)
@click.option(
    "--data-quality",
    "data_quality_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=None,
    help="Optional data_quality_warnings.csv (from analyze-data-quality) to include as its own report section.",
)
@click.option(
    "--top-changes",
    "top_changes_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=None,
    help="Optional top_changes.csv (from analyze-top-changes) to include as its own report section.",
)
@click.option(
    "--clusters",
    "clusters_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=None,
    help="Optional clusters.csv (from build-clusters) to include as its own report section.",
)
@click.option(
    "--priority-areas",
    "priority_areas_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=None,
    help="Optional priority_areas.csv (from build-priority-areas) to include as its own report section.",
)
@click.option(
    "--verbosity",
    type=click.Choice(VERBOSITY_LEVELS),
    default="standard",
    show_default=True,
    help="summary: executive summary + priority areas only. standard: adds clusters/top changes/"
    "data quality/questions/findings. full: adds all appendices.",
)
@click.option("--out", "out_path", type=click.Path(path_type=Path), required=True)
def report_cmd(
    findings_path: Path,
    reconcile_specs: tuple[str, ...],
    data_quality_path: Path | None,
    top_changes_path: Path | None,
    clusters_path: Path | None,
    priority_areas_path: Path | None,
    verbosity: str,
    out_path: Path,
) -> None:
    """Render a citizen-readable markdown report from findings and reconciliation summaries."""
    reconcile_paths = _parse_reconcile_specs(reconcile_specs)
    summaries = [load_reconcile_summary(fund, path) for fund, path in sorted(reconcile_paths.items())]
    render_report(
        findings_path,
        summaries,
        out_path,
        data_quality_path=data_quality_path,
        top_changes_path=top_changes_path,
        clusters_path=clusters_path,
        priority_areas_path=priority_areas_path,
        verbosity=verbosity,
    )
    console.print(f"wrote {out_path}")


@main.command("generate-report")
@click.option(
    "--rows",
    "row_paths",
    multiple=True,
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    required=True,
    help="Reviewed/corrected row CSVs to consolidate (repeatable, order preserved).",
)
@click.option(
    "--reconcile",
    "reconcile_specs",
    multiple=True,
    required=True,
    help="fund=path pairs, repeatable.",
)
@click.option("--out-dir", "out_dir", type=click.Path(path_type=Path), required=True)
@click.option("--reports-dir", "reports_dir", type=click.Path(path_type=Path), default=Path("reports"), show_default=True)
@click.option("--report-filename", default="weakley-fwm-2026-06-30.md", show_default=True)
@click.option("--min-absolute", default=5000, show_default=True, type=int)
@click.option("--min-percent", default=15, show_default=True, type=int)
@click.option(
    "--require-both/--either",
    "require_both",
    default=True,
    show_default=True,
    help="Require both absolute and percent thresholds to flag material, or trigger on either.",
)
@click.option(
    "--verbosity",
    type=click.Choice(VERBOSITY_LEVELS),
    default="standard",
    show_default=True,
    help="summary: executive summary + priority areas only. standard: adds clusters/top changes/"
    "data quality/questions/findings. full: adds all appendices.",
)
def generate_report_cmd(
    row_paths: tuple[Path, ...],
    reconcile_specs: tuple[str, ...],
    out_dir: Path,
    reports_dir: Path,
    report_filename: str,
    min_absolute: int,
    min_percent: int,
    require_both: bool,
    verbosity: str,
) -> None:
    """Run consolidate -> analyze-deltas -> analyze-compensation -> build-clusters ->
    analyze-top-changes -> build-findings -> analyze-data-quality -> build-priority-areas -> report
    end to end."""
    reconcile_paths = _parse_reconcile_specs(reconcile_specs)
    threshold = MaterialityThreshold(
        min_absolute=Decimal(min_absolute), min_percent=Decimal(min_percent), require_both=require_both
    )
    stats = run_report_workflow(
        list(row_paths), reconcile_paths, out_dir, reports_dir, report_filename, threshold, verbosity
    )
    console.print(
        f"report complete: {stats['consolidated_rows']} rows consolidated; "
        f"{stats['material_rows']} material deltas; {stats['new_line_rows']} new; "
        f"{stats['eliminated_line_rows']} eliminated; "
        f"{stats['compensation_needs_review']} compensation rows need review; "
        f"{stats['data_quality_warnings']} data-quality warnings "
        f"({stats['high_impact_data_quality_warnings']} high-impact); "
        f"{stats['top_change_rows']} top-change rows; "
        f"{stats['clusters']} clusters ({stats['paired_clusters']} paired); "
        f"{stats['whole_fund_structural_changes']} whole-fund structural change(s); "
        f"{stats['grant_capital_pairs']} grant/capital pair(s); "
        f"{stats['manual_corrections']} manual correction(s); "
        f"{stats['priority_areas']} priority area(s); "
        f"{stats['total_findings']} total findings"
    )
    console.print(f"wrote report to {reports_dir / report_filename}")


if __name__ == "__main__":
    main()
