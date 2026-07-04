# Checkpoint: Weakley FWM 2026-06-30 Fund 202 pages 156-158

## Scope

Reviewed packet range: pages 156-158.

Covered fund:

- Fund 202 Nursing Home

Fund 202 begins on page 156 and runs to page 158, the last page of the packet's budget-table section. **This is the last fund in the packet** -- with this checkpoint, all funds in the 2026-06-30 Finance, Ways, and Means packet (101, 116, 122, 131, 141, 143, 151, 171, 172, 202) are extracted, reviewed, corrected, and reconciled.

## Reproducible command chain

    budget-audit run-reviewed-range data/interim/ocr \
      --pages 156-158 \
      --document-id weakley-fwm-2026-06-30 \
      --page-review review/weakley-fwm-2026-06-30/page_review_156_158.csv \
      --corrections review/weakley-fwm-2026-06-30/manual_row_corrections_156_158.csv \
      --out-dir data/processed \
      --funds 202

    budget-audit reconcile-subtotals data/processed/ocr_table_rows_156_158_corrected.csv \
      --out data/processed/subtotal_mismatches_156_158.csv

(Pages 156-158 were already rendered and OCR'd as part of the full-packet OCR pass.)

## Row counts

| Metric | Count |
|---|---:|
| Extracted OCR rows | 36 |
| Classified rows | 36 |
| Replaced rows | 0 |
| Added rows | 2 |
| Review rows | 0 |
| Unparsed amounts | 0 |

## Reconciliation checkpoint

| Fund | Revenue with transfers | Expenditure with transfers | Net |
|---:|---:|---:|---:|
| 202 | 0 | 0 | 0 |

Matches the packet's own printed "Excess of Estimated Revenues & Other Sources Over/(Under) Estimated Expenditures" figure for FY 2026-27 (`0`) exactly.

## Subtotal-level reconciliation

    4 groups compared; 4 matched; 0 mismatched; 4 roll-up totals skipped

## Notes

Fund 202 is **entirely zeroed out for FY 2026-27** across every line item -- revenue, expenditures, transfers, and net all budget to `0`. The `Estimated Fund Balance - June 30` line on the summary page also reads `0` for both the current and prior estimate. Taken together, this reads as a fund being wound down or fully depleted, not an extraction artifact -- every underlying line item independently prints `0` for the FY 2026-27 column, not just the totals.

Because every `budget_26_27` value in the fund is genuinely `0`, missing rows have zero numeric impact on reconciliation regardless of correction -- but two rows were still corrected for data-quality completeness, consistent with this project's "never discard source text" principle:

- **`335 Maintenance/Repair - Buildings`** and **`435 Office Supplies`** both failed extraction because their `actual_25_26` field is a garbled OCR character sequence (`i¢}` and `ie}` respectively) outside `ACCOUNT_ROW_RE`'s amount-field character class -- the same artifact pattern documented in the Fund 151 checkpoint. Both were added via correction to preserve their `actual_24_25` history ($2,749 and $1,580), with the garbled field read as `0`, consistent with every other value on this all-zero-budget page.

Two further OCR issues were identified but **deliberately left uncorrected**, since neither loses information or affects reconciliation:

- The revenue section's total reads **"Total From Federal Sources"**, but the underlying accounts (`43120`, `44110`, `44170`) are in the 43xxx/44xxx local-revenue range, under a "REVENUE FROM LOCAL SOURCES" header -- the same mislabeling pattern seen in the Fund 172 checkpoint (also on state/local-range accounts misread as "Federal"). Not corrected, for the same reason as before: rewriting an inferred text label is a bigger leap than an arithmetic-verified numeric correction. Flagged here for human review.
- Page 156 has a heavily garbled second total line (`"1ULal CoUITatcU RevelUuTD & UYUIET ..."`, evidently a garbled "Total Estimated Revenue & Other Sources") that fails `TOTAL_ROW_RE`'s match entirely (the label doesn't recognizably start with "total"). This is a pure roll-up restatement of the "Total From Federal Sources" line directly above it -- since Local Sources is the fund's *only* revenue category, the two totals are identical -- so no information is lost by it not extracting.

## Current covered funds — full packet

All funds in the 2026-06-30 packet are now reconciled:

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
| 172 | Reconciled in pages 153-155 checkpoint |
| 202 | Reconciled in this checkpoint |

## Next work

- Fund extraction is complete for this packet. Move to Phase 5 analysis work adopting the `docs/report-design.md` taxonomy (issue #12) -- clustering, the fuller finding taxonomy, pairing detection, public-records question generation, and re-running the report against all 10 reconciled funds.
- Investment Policy amendment diff (Resolution 2026-52, issue #10) remains separate document/policy-text work, not fund extraction.
- Raw public PDF storage policy (issue #11) remains undecided.
- Consider issue #14 (`corrections.py` add-action `row_type` limitation), which surfaced again as a design constraint during this fund's corrections (though not triggered here since all affected values were zero).
