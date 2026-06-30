from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from budget_audit.corrections import apply_row_corrections
from budget_audit.enrich import enrich_ocr_rows_with_page_review
from budget_audit.ocr_table_rows import extract_ocr_table_rows
from budget_audit.reconcile import reconcile_fund
from budget_audit.review import build_ocr_review_queue
from budget_audit.row_classify import classify_ocr_rows
from budget_audit.summarize import summarize_classified_ocr_rows


@dataclass(frozen=True)
class ReviewedRangeWorkflowPaths:
    raw_rows: Path
    enriched_rows: Path
    classified_rows: Path
    corrected_rows: Path
    review_queue: Path


def safe_page_label(page_spec: str) -> str:
    return page_spec.replace(",", "_").replace("-", "_").replace(" ", "")


def reviewed_range_paths(out_dir: Path, page_spec: str) -> ReviewedRangeWorkflowPaths:
    label = safe_page_label(page_spec)
    return ReviewedRangeWorkflowPaths(
        raw_rows=out_dir / f"ocr_table_rows_{label}.csv",
        enriched_rows=out_dir / f"ocr_table_rows_{label}_enriched.csv",
        classified_rows=out_dir / f"ocr_table_rows_{label}_classified.csv",
        corrected_rows=out_dir / f"ocr_table_rows_{label}_corrected.csv",
        review_queue=out_dir / f"ocr_review_queue_{label}_corrected.csv",
    )


def parse_fund_list(fund_spec: str) -> list[str]:
    return [fund.strip() for fund in fund_spec.split(",") if fund.strip()]


def run_reviewed_range_workflow(
    ocr_dir: Path,
    *,
    page_spec: str,
    pages: set[int],
    document_id: str,
    page_review_path: Path,
    corrections_path: Path | None,
    out_dir: Path,
    funds: list[str],
) -> dict[str, int]:
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = reviewed_range_paths(out_dir, page_spec)

    raw_rows = extract_ocr_table_rows(ocr_dir, paths.raw_rows, document_id, pages=pages)
    enriched_rows = enrich_ocr_rows_with_page_review(paths.raw_rows, page_review_path, paths.enriched_rows)
    classified_rows = classify_ocr_rows(paths.enriched_rows, paths.classified_rows)

    if corrections_path is None:
        correction_stats = {"replaced": 0, "added": 0}
        corrected_source = paths.classified_rows
    else:
        correction_stats = apply_row_corrections(paths.classified_rows, corrections_path, paths.corrected_rows)
        corrected_source = paths.corrected_rows

    review_rows = build_ocr_review_queue(corrected_source, paths.review_queue)
    summary_stats = summarize_classified_ocr_rows(corrected_source, out_dir)

    reconciled_funds = 0
    for fund in funds:
        reconcile_fund(corrected_source, out_dir / f"reconcile_fund_{fund}_{safe_page_label(page_spec)}.csv", fund)
        reconciled_funds += 1

    return {
        "raw_rows": raw_rows,
        "enriched_rows": enriched_rows,
        "classified_rows": classified_rows,
        "replaced_rows": correction_stats["replaced"],
        "added_rows": correction_stats["added"],
        "review_rows": review_rows,
        "summary_line_rows": summary_stats["line_rows"],
        "summary_non_line_rows": summary_stats["non_line_rows"],
        "summary_unparsed_amounts": summary_stats["unparsed_amounts"],
        "reconciled_funds": reconciled_funds,
    }
