# Checkpoint: Weakley FWM 2026-06-30 pages 23-85

## Scope

Reviewed packet range: pages 23-85.

Covered funds:

- Fund 101 General
- Fund 116 Solid Waste/Sanitation
- Fund 122 Drug Enforcement
- Fund 131 Highway

Fund 141 begins on page 86 and is the next extraction target.

## Reproducible command chain

    budget-audit extract-ocr-rows data/interim/ocr \
      --pages 23-85 \
      --document-id weakley-fwm-2026-06-30 \
      --out data/processed/ocr_table_rows_023_085.csv

    budget-audit enrich-ocr-rows data/processed/ocr_table_rows_023_085.csv \
      --page-review review/weakley-fwm-2026-06-30/page_review_023_085.csv \
      --out data/processed/ocr_table_rows_023_085_enriched.csv

    budget-audit classify-ocr-rows data/processed/ocr_table_rows_023_085_enriched.csv \
      --out data/processed/ocr_table_rows_023_085_classified.csv

    budget-audit apply-row-corrections data/processed/ocr_table_rows_023_085_classified.csv \
      --corrections review/weakley-fwm-2026-06-30/manual_row_corrections_023_085.csv \
      --out data/processed/ocr_table_rows_023_085_corrected.csv

## Row counts

| Metric | Count |
|---|---:|
| Extracted OCR rows | 847 |
| Corrected rows | 850 |
| Replaced rows | 1 |
| Added rows | 3 |

## Reconciliation checkpoint

| Fund | Revenue | Expenditure | Net |
|---:|---:|---:|---:|
| 101 | 14,057,984 | 14,062,391 | -4,407 |
| 116 | 45,500 | 52,998 | -7,498 |
| 122 | 20,650 | 30,100 | -9,450 |
| 131 | 7,909,610 | 7,868,699 | 40,911 |

## Next work

- Add a single runner command for the 23-85 workflow.
- Add subtotal-level reconciliation.
- Extend page-review metadata into Fund 141.
- Start analysis outputs for deltas, materiality, and compensation summaries.
