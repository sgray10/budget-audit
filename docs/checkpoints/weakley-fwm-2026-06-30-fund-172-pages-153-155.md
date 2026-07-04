# Checkpoint: Weakley FWM 2026-06-30 Fund 172 pages 153-155

## Scope

Reviewed packet range: pages 153-155.

Covered fund:

- Fund 172 Community Development

Fund 172 begins on page 153. The next fund, Fund 202 Nursing Home, begins on page 156, so this checkpoint treats pages 153-155 as the reviewed Fund 172 range.

## Reproducible command chain

    budget-audit run-reviewed-range data/interim/ocr \
      --pages 153-155 \
      --document-id weakley-fwm-2026-06-30 \
      --page-review review/weakley-fwm-2026-06-30/page_review_153_155.csv \
      --corrections review/weakley-fwm-2026-06-30/manual_row_corrections_153_155.csv \
      --out-dir data/processed \
      --funds 172

    budget-audit reconcile-subtotals data/processed/ocr_table_rows_153_155_corrected.csv \
      --out data/processed/subtotal_mismatches_153_155.csv

(Pages 153-155 were already rendered and OCR'd as part of the full-packet OCR pass.)

## Row counts

| Metric | Count |
|---|---:|
| Extracted OCR rows | 9 |
| Classified rows | 9 |
| Replaced rows | 0 |
| Added rows | 3 |
| Review rows | 0 |
| Unparsed amounts | 0 |

## Reconciliation checkpoint

| Fund | Revenue with transfers | Expenditure with transfers | Net |
|---:|---:|---:|---:|
| 172 | 1,579,857 | 1,755,396 | -175,539 |

Matches the packet's own printed "Excess of Estimated Revenues & Other Sources Over/(Under) Estimated Expenditures" figure for FY 2026-27 (`(175,539)`) exactly.

## Subtotal-level reconciliation

    3 groups compared; 3 matched; 0 mismatched; 4 roll-up totals skipped

## Notes

Fund 172's revenue page (153) has the worst OCR quality of any fund checkpointed so far -- three of its five line items and two of its three section-total lines failed extraction entirely:

- **`46980 Other State Grants - Connected Communities Facilities`** ($1,579,857, the entire fund's revenue) failed extraction because its label wraps to a second physical line ("Communities Facilities") and its amount fields contain a stray em-dash character (`—-`) not in `ACCOUNT_ROW_RE`'s character class. Added via correction after hand-summing the fund's Total Estimated Revenues to confirm this single row accounts for the entire total.
- **`48610 Donations`** and **`49800 Transfers In`** both failed extraction because the source prints only 3 of their 4 amount fields on the account-code line, with the 4th (`budget_26_27`) landing on its own garbled OCR line (literally `Oo`, read as a zero) instead of on the row's own line. Both were confirmed as `budget_26_27 = 0` via the same fund-level arithmetic check, then added via correction.
- **Two "Total From Other Government and Citiezens Group Sources" total lines** (closing the Donations and Transfers In sections respectively) failed extraction for the same split-4th-field reason. The first is legible enough to reconstruct with confidence; the **second is not** (only a bare `0` is legible in `... Citiezens Group Sources serio : 0`, with the other three columns illegible) and was deliberately left uncorrected rather than guessed at. **Neither total line was added at all** -- see the row-type limitation below, which made adding them actively counterproductive rather than merely incomplete.
- **The revenue section's first total line reads "Total From Federal Sources"**, but the account (`46980`) is in the 46xxx range and sits under a "REVENUE FROM STATE SOURCES" header, consistent with every other fund's account-prefix convention (46xxx = state, 47xxx = federal) seen throughout this packet. This is very likely an OCR misread of "State" as "Federal", but the label was **not corrected** -- inferring and rewriting a text label carries more risk of being wrong than the numeric corrections above, which were verified by arithmetic. Flagged here for human review rather than silently fixed.

**New limitation discovered and filed as [issue #14](https://github.com/sgray10/budget-audit/issues/14):** `apply_row_corrections()`'s `add` action hardcodes `row_type="line_item"` for every added row, with no way to add a `transfer` or `total` row correctly. This is why the two "Total From Other..." total lines were not added via correction -- doing so would have forced them to `row_type="line_item"`, and since `reconcile-subtotals` only closes a group on `row_type == "total"`, they would not have closed their own group; instead they'd merge into whichever *real* total row came next, potentially producing a confusing mismatch. The same limitation affected `49800 Transfers In`, which was added but landed as `row_type="line_item"` instead of `transfer` -- harmless here only because its value is $0.

As a result of leaving those two total lines out, the Donations (`48610`) and Transfers In (`49800`) line items -- both $0 for FY 2026-27 -- end up grouped together with Fund 172's Contracted Services line item (`310`, also $0) under that Sub-Total instead of under their own (unextracted) totals. This produces a coincidentally-correct match (0+0+0 = 0) rather than a conceptually clean one; documented here so it isn't mistaken for intentional grouping logic. Because every value involved is exactly zero, this does not affect the fund's reconciliation or the subtotal-mismatch output's correctness for this checkpoint -- it would matter for a future fund where the equivalent lines are nonzero.

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
| 171 | Reconciled in pages 150-152 checkpoint |
| 172 | Reconciled in this checkpoint |

## Next work

- Continue extraction with Fund 202 Nursing Home, pages 156-158 -- the last fund in the packet. See issue #9.
- Once Fund 202 is done, move to Phase 5 analysis work adopting the `docs/report-design.md` taxonomy. See issue #12.
- Consider fixing issue #14 (corrections.py add-action row_type) before or during Fund 202 if a similar gap is found there.
