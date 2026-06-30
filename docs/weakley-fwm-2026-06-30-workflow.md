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

## Current extraction checkpoint

As of the current OCR workflow:

| Metric | Count |
|---|---:|
| OCR table rows extracted | 825 |
| Classified line items | 823 |
| Excluded non-line rows | 2 |
| Unparsed `budget_26_27` amounts | 0 |

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
