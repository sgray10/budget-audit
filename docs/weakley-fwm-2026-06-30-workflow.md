# Weakley County FWM 2026-06-30 Packet Workflow

This document records the current reproducible workflow for extracting structured budget rows from the Weakley County Finance, Ways, and Means packet dated 2026-06-30.

## Source document

Expected local path:

    data/raw/FWM-Meeting-Packet-6-30-26.pdf

Generated local artifacts are intentionally kept under `data/` and should not be committed unless explicitly promoted.

## Current workflow

Render the budget packet pages to images:

    budget-audit render-pages data/raw/FWM-Meeting-Packet-6-30-26.pdf \
      --pages 23-80 \
      --out data/interim/rendered \
      --dpi 200

OCR the rendered pages:

    budget-audit ocr-pages data/interim/rendered \
      --pages 23-80 \
      --out data/interim/ocr

Extract likely budget table rows from OCR text:

    budget-audit extract-ocr-rows data/interim/ocr \
      --document-id weakley-fwm-2026-06-30 \
      --out data/processed/ocr_table_rows.csv

Enrich extracted rows with page-review metadata:

    budget-audit enrich-ocr-rows data/processed/ocr_table_rows.csv \
      --page-review review/weakley-fwm-2026-06-30/page_review_023_080.csv \
      --out data/processed/ocr_table_rows_enriched.csv

Classify rows by row type and category:

    budget-audit classify-ocr-rows data/processed/ocr_table_rows_enriched.csv \
      --out data/processed/ocr_table_rows_classified.csv

Summarize classified rows:

    budget-audit summarize-ocr-rows data/processed/ocr_table_rows_classified.csv \
      --out-dir data/processed

Create an OCR review queue:

    budget-audit review-ocr-rows data/processed/ocr_table_rows_classified.csv \
      --out data/processed/ocr_review_queue.csv

## Current extraction checkpoint

As of the current OCR workflow:

| Metric | Count |
|---|---:|
| OCR table rows extracted | 825 |
| Classified line items | 823 |
| Excluded non-line rows | 2 |
| Unparsed `budget_26_27` amounts | 0 |
| OCR review queue rows | 2 |

## Current summary by fund and budget side

| Fund | Fund name | Budget side | 2026-27 total |
|---|---|---|---:|
| 101 | General | revenue | 14,013,957 |
| 101 | General | expenditure | 14,062,391 |
| 116 | Solid Waste/Sanitation | expenditure | 98,498 |
| 122 | Drug Enforcement | expenditure | 50,750 |
| 131 | Highway/Public Works | expenditure | 13,668,822 |

## Excluded non-line rows

| Fund | Row type | Label | 2026-27 total |
|---|---|---|---:|
| 101 General | transfer | Transfers In | 44,027 |
| 101 General | transfer | Transfers to Other Funds | 0 |

## Notes and cautions

The current page review metadata is coarse first-pass metadata for pages 23-80. It should be refined with visual review.

The current row classification separates obvious transfers from line items. Future passes should add stronger row types such as subtotal, total, fund balance, and review-required.

The current summaries are OCR-derived and should be treated as reviewable working data, not final audited figures.

## Next useful improvements

1. Add a review queue for OCR rows with suspicious characters, questionable account codes, or unlikely amount patterns.
2. Convert prototype scripts into stable CLI commands or remove them after parity is confirmed.
3. Add tests for OCR row extraction, enrichment, classification, and summary helpers.
4. Add CI so pushes run pytest, ruff, and mypy automatically.


## Current OCR review queue

Current flagged rows after OCR cleanup:

| Page | Account | Label | Reason | Note |
|---:|---:|---|---|---|
| 49 | 212 | Medicare Liability | suspicious raw character | Raw OCR includes `§22`; likely requires visual confirmation. |
| 66 | 316 | OPIA West Tennessee United Way | suspicious budget_25_26 | Raw OCR includes a stray `.` amount artifact. |

## Fund 101 reconciliation checkpoint

The classified OCR rows can be reconciled with:

    budget-audit reconcile data/processed/ocr_table_rows_classified.csv \
      --fund 101 \
      --out data/processed/reconcile_fund_101.csv

Current Fund 101 reconciliation:

| Metric | Value |
|---|---:|
| Revenue line items | 14,013,957 |
| Transfers in | 44,027 |
| Revenue with transfers | 14,057,984 |
| Expenditure line items | 14,062,391 |
| Transfers out | 0 |
| Expenditure with transfers | 14,062,391 |
| Net line items | -48,434 |
| Net with transfers | -4,407 |
| Unparsed amounts | 0 |

This suggests Fund 101 is close to balanced in the OCR-derived working dataset, with a net difference of -4,407 after transfers.

## Analysis and report generation

Once a page range is reconciled and checkpointed, it can be folded into the citizen-readable report. This is separate from the extraction chain above and works from the `_corrected` row CSVs for each reviewed range.

Consolidate the reviewed/corrected row CSVs (disjoint page ranges, so this is a plain concatenation -- add a third `--rows`/path when Fund 143 is added):

    budget-audit consolidate-reviewed-rows \
      data/processed/ocr_table_rows_023_085_corrected.csv \
      data/processed/ocr_table_rows_86_138_corrected.csv \
      --out data/processed/reviewed_funds_rows.csv

Compute year-over-year deltas and flag material changes (default: both an absolute-dollar floor of $5,000 and a percent floor of 15% must be exceeded, to avoid flooding the report with small-dollar lines that swing wildly by percent):

    budget-audit analyze-deltas data/processed/reviewed_funds_rows.csv \
      --out-dir data/processed

Roll up compensation-category rows and flag ones that plausibly identify an individual position rather than an aggregate category:

    budget-audit analyze-compensation data/processed/reviewed_funds_rows.csv \
      --out-dir data/processed

Assemble findings. `--reconcile fund=path` must point at the corrected/authoritative reconcile file for each fund -- several stale duplicates exist locally (see note below), so this is deliberately explicit rather than globbed:

    budget-audit build-findings data/processed/line_item_deltas.csv \
      --compensation-flags data/processed/compensation_flags.csv \
      --reconcile 101=data/processed/reconcile_fund_101_023_085.csv \
      --reconcile 116=data/processed/reconcile_fund_116_023_085.csv \
      --reconcile 122=data/processed/reconcile_fund_122_023_085.csv \
      --reconcile 131=data/processed/reconcile_fund_131_023_085_corrected.csv \
      --reconcile 141=data/processed/reconcile_fund_141_86_138.csv \
      --out data/processed/findings.csv

Render the markdown report:

    budget-audit report data/processed/findings.csv \
      --reconcile 101=data/processed/reconcile_fund_101_023_085.csv \
      --reconcile 116=data/processed/reconcile_fund_116_023_085.csv \
      --reconcile 122=data/processed/reconcile_fund_122_023_085.csv \
      --reconcile 131=data/processed/reconcile_fund_131_023_085_corrected.csv \
      --reconcile 141=data/processed/reconcile_fund_141_86_138.csv \
      --out reports/weakley-fwm-2026-06-30.md

Or run the full chain in one command:

    budget-audit generate-report \
      --rows data/processed/ocr_table_rows_023_085_corrected.csv \
      --rows data/processed/ocr_table_rows_86_138_corrected.csv \
      --reconcile 101=data/processed/reconcile_fund_101_023_085.csv \
      --reconcile 116=data/processed/reconcile_fund_116_023_085.csv \
      --reconcile 122=data/processed/reconcile_fund_122_023_085.csv \
      --reconcile 131=data/processed/reconcile_fund_131_023_085_corrected.csv \
      --reconcile 141=data/processed/reconcile_fund_141_86_138.csv \
      --out-dir data/processed --reports-dir reports --report-filename weakley-fwm-2026-06-30.md

**Note on stale duplicate files:** `data/processed/reconcile_fund_131_023_085.csv` and `reconcile_fund_131_23_85.csv` both hold a pre-correction number (revenue_line_items=7,939,610); only `reconcile_fund_131_023_085_corrected.csv` (7,909,610) is correct and must be the one referenced above.

### First analysis/report checkpoint

| Metric | Count |
|---|---:|
| Consolidated rows (funds 101, 116, 122, 131, 141) | 1,547 |
| Line items analyzed | 1,543 |
| Material year-over-year changes (headline actual 25-26 -> budget 26-27, both $5,000 and 15% thresholds) | 250 |
| New line items | 0 |
| Eliminated line items | 0 |
| Compensation rows flagged needs_review | 3 |
| Reconciliation findings (funds not reconciling within $100 tolerance) | 5 |
| Total findings | 258 |

All 5 covered funds' reconciliation totals in the rendered report match the checkpoint numbers above exactly. Report output: `reports/weakley-fwm-2026-06-30.md`.

Zero new/eliminated line items reflects this dataset specifically -- every reviewed line item has both an `actual_25_26` and a `budget_26_27` value, so nothing is missing on either side of the headline comparison. This may not hold once Fund 143+ is added.

The compensation `contains_salary_or_compensation` field is page-level metadata (set by page-review enrichment, true for the whole page), not a per-row signal -- `analyze-compensation` filters on the row-level `category == "compensation"` classification only.
