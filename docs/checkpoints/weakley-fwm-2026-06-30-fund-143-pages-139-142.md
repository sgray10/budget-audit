# Checkpoint: Weakley FWM 2026-06-30 Fund 143 pages 139-142

## Scope

Reviewed packet range: pages 139-142.

Covered fund:

- Fund 143 Child Nutrition (labeled "School Nutrition" in the meeting agenda; the packet's own page headers read "Fund: Child Nutrition")

Fund 143 begins on page 139. The next fund, Fund 151 Debt Service, begins on page 143, so this checkpoint treats pages 139-142 as the reviewed Fund 143 range.

## Reproducible command chain

    budget-audit run-reviewed-range data/interim/ocr \
      --pages 139-142 \
      --document-id weakley-fwm-2026-06-30 \
      --page-review review/weakley-fwm-2026-06-30/page_review_139_142.csv \
      --corrections review/weakley-fwm-2026-06-30/manual_row_corrections_139_142.csv \
      --out-dir data/processed \
      --funds 143

    budget-audit reconcile-subtotals data/processed/ocr_table_rows_139_142_corrected.csv \
      --out data/processed/subtotal_mismatches_139_142.csv

(Pages 139-142 were already rendered and OCR'd as part of the full-packet OCR pass; `render-pages`/`ocr-pages` did not need to be rerun.)

## Row counts

| Metric | Count |
|---|---:|
| Extracted OCR rows | 58 |
| Classified rows | 58 |
| Replaced rows | 4 |
| Added rows | 1 |
| Review rows | 0 |
| Unparsed amounts | 0 |

## Reconciliation checkpoint

| Fund | Revenue with transfers | Expenditure with transfers | Net |
|---:|---:|---:|---:|
| 143 | 3,621,955 | 3,621,955 | 0 |

Fund 143's proposed FY 2026-27 budget is exactly balanced (revenue equals expenditure), matching the packet's own printed "Total Estimated Revenue & Other Sources" / "Total Estimated Expenditures" figures exactly.

## Subtotal-level reconciliation

    9 groups compared; 9 matched; 0 mismatched; 5 roll-up totals skipped

Every `Sub-Total`/`Total` line in the fund reconciles exactly against the sum of its preceding line items, with zero mismatches — the cleanest result of any fund checkpointed so far.

## Notes

Fund 143 is much smaller and cleaner than Fund 141 (4 pages vs. 53), but showed two of the same OCR patterns documented in the Fund 141 checkpoint, at smaller scale:

- **FTE count fused into the `actual_24_25` amount column**, on 4 Personal Services rows (e.g. source `"1 75,480"` for Director, extracted as `"175,480"`). Confirmed by hand-summing the Personal Services Sub-Total's `budget_26_27` column (unaffected by this artifact) before writing any correction, then fixing `actual_24_25` via `replace` corrections for data-quality/delta-analysis accuracy — this did not affect any reconciliation number, since `budget_26_27` was never corrupted.
- **A dotted account code (`47114.`) broke `ACCOUNT_ROW_RE`'s match**, silently dropping one row (`SNACK USDA - Snacks`, $35,000) from extraction entirely. Caught by hand-summing "Total From Federal Sources" before correcting: the gap ($35,000) matched the missing row's `budget_26_27` value exactly. Fixed via an `add` correction with the correct document-order `line_number` (38, between the two adjacent `47114` rows) so it doesn't corrupt subtotal grouping order.

Both corrections were verified with `apply-row-corrections --strict` (zero unmatched/ambiguous) before being treated as final, and the full reconciliation was hand-verified column-by-column against the raw OCR text before any correction was written — every subtotal in the fund ties out exactly to the corrected line-item sums.

A review.py false-positive was also fixed as part of this checkpoint: total/subtotal rows have no account number by design, but `review.py`'s `suspicious_account` check didn't know that, so every one of the newly-extracted total rows (see the subtotal-reconciliation PR) was being flagged as suspicious. Fixed to exempt `row_type == "total"` rows from the account check, dropping Fund 143's review queue from 14 false-positive rows to 0, with no loss of genuine flags (re-verified against the already-checkpointed 23-85 and 86-138 ranges: all previously-known flags, e.g. the page-49 `§22` artifact and the page-66 stray-dot artifact, are still caught).

## Current covered funds

The reviewed/reconciled packet coverage now includes:

| Fund | Status |
|---:|---|
| 101 | Reconciled in pages 23-85 checkpoint |
| 116 | Reconciled in pages 23-85 checkpoint |
| 122 | Reconciled in pages 23-85 checkpoint |
| 131 | Reconciled in pages 23-85 checkpoint |
| 141 | Reconciled in pages 86-138 checkpoint |
| 143 | Reconciled in this checkpoint |

## Next work

- Continue extraction with Fund 151 Debt Service, pages 143-149.
- Fund 171 (General Capital Projects, pages 150-152), Fund 172 (Community Development, pages 153-155), and Fund 202 (Nursing Home, pages 156-158) remain after that.
- The Investment Policy amendment (Resolution 2026-52) is separate document/policy-text analysis, not fund extraction -- tracked separately.
