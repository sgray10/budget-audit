# Checkpoint: Weakley FWM 2026-06-30 Fund 171 pages 150-152

## Scope

Reviewed packet range: pages 150-152.

Covered fund:

- Fund 171 General Capital Projects

Fund 171 begins on page 150. The next fund, Fund 172 Community Development, begins on page 153, so this checkpoint treats pages 150-152 as the reviewed Fund 171 range.

## Reproducible command chain

    budget-audit run-reviewed-range data/interim/ocr \
      --pages 150-152 \
      --document-id weakley-fwm-2026-06-30 \
      --page-review review/weakley-fwm-2026-06-30/page_review_150_152.csv \
      --corrections review/weakley-fwm-2026-06-30/manual_row_corrections_150_152.csv \
      --out-dir data/processed \
      --funds 171

    budget-audit reconcile-subtotals data/processed/ocr_table_rows_150_152_corrected.csv \
      --out data/processed/subtotal_mismatches_150_152.csv

(Pages 150-152 were already rendered and OCR'd as part of the full-packet OCR pass.)

**Update (2026-07-04):** `manual_row_corrections_150_152.csv` is an empty (header-only) corrections file, added so this fund produces a real `ocr_table_rows_150_152_corrected.csv` with the same column schema as every other fund's corrected file. Originally this fund's `run-reviewed-range` was invoked without `--corrections` at all (genuinely no corrections were needed), which left only a `_classified.csv` file -- missing the `correction_action`/`correction_reason`/`correction_raw_line` columns every other fund's file has. That schema mismatch broke `consolidate-reviewed-rows`' (deliberately strict) header check when building a report across all 10 funds. Reconciliation numbers are unaffected (confirmed identical before and after).

## Row counts

| Metric | Count |
|---|---:|
| Extracted OCR rows | 13 |
| Classified rows | 13 |
| Replaced rows | 0 |
| Added rows | 0 |
| Review rows | 0 |
| Unparsed amounts | 0 |

## Reconciliation checkpoint

| Fund | Revenue with transfers | Expenditure with transfers | Net |
|---:|---:|---:|---:|
| 171 | 0 | 37,524 | -37,524 |

Matches the packet's own printed "Excess of Estimated Revenues & Other Sources Over/(Under) Estimated Expenditures" figure for FY 2026-27 (`(37,524)`) exactly.

## Subtotal-level reconciliation

    3 groups compared; 3 matched; 0 mismatched; 6 roll-up totals skipped

## Notes

Fund 171 is the smallest and cleanest fund checkpointed so far: 13 rows across 3 pages, **zero OCR extraction issues, zero corrections needed, zero review-queue flags**. No dotted-account-code gaps, no FTE-fusion artifacts, no garbled totals -- every row extracted cleanly on the first pass and every subtotal matched exactly, hand-verified against the raw OCR text before running any tooling.

One structural point worth noting for future funds: the fund's only "Other Charges" line is `590 Transfers to Other Funds` ($37,524 for FY 2026-27), which `row_classify.py` correctly classifies as `row_type="transfer"`, not `line_item`. `reconcile-subtotals` only sums `line_item` rows when comparing to a total row, so this Sub-Total (whose only contributor is a transfer row) is correctly treated as a zero-line-item roll-up and skipped, rather than reported as a false mismatch -- the transfer amount is still captured correctly in fund-level reconciliation via `reconcile_fund()`'s separate `transfer_out` tracking, matching the packet's own numbers exactly.

## Current covered funds

The reviewed/reconciled packet coverage now includes:

| Fund | Status |
|---:|---|
| 101 | Reconciled in pages 23-85 checkpoint |
| 116 | Reconciled in pages 23-85 checkpoint |
| 122 | Reconciled in pages 23-85 checkpoint |
| 131 | Reconciled in pages 23-85 checkpoint |
| 141 | Reconciled in pages 86-138 checkpoint |
| 143 | Reconciled in pages 139-142 checkpoint |
| 151 | Reconciled in pages 143-149 checkpoint |
| 171 | Reconciled in this checkpoint |

## Next work

- Continue extraction with Fund 172 Community Development, pages 153-155. See issue #8.
- Fund 202 (Nursing Home, pages 156-158) after that. See issue #9.
- Once all funds are extracted, move to Phase 5 analysis work adopting the `docs/report-design.md` taxonomy. See issue #12.
