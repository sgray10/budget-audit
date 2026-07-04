# Checkpoint: Weakley FWM 2026-06-30 Fund 151 pages 143-149

## Scope

Reviewed packet range: pages 143-149.

Covered fund:

- Fund 151 Debt Service

Fund 151 begins on page 143. The next fund, Fund 171 General Capital Projects, begins on page 150, so this checkpoint treats pages 143-149 as the reviewed Fund 151 range.

## Reproducible command chain

    budget-audit run-reviewed-range data/interim/ocr \
      --pages 143-149 \
      --document-id weakley-fwm-2026-06-30 \
      --page-review review/weakley-fwm-2026-06-30/page_review_143_149.csv \
      --corrections review/weakley-fwm-2026-06-30/manual_row_corrections_143_149.csv \
      --out-dir data/processed \
      --funds 151

    budget-audit reconcile-subtotals data/processed/ocr_table_rows_143_149_corrected.csv \
      --out data/processed/subtotal_mismatches_143_149.csv

(Pages 143-149 were already rendered and OCR'd as part of the full-packet OCR pass.)

## Row counts

| Metric | Count |
|---|---:|
| Extracted OCR rows | 47 |
| Classified rows | 47 |
| Replaced rows | 0 |
| Added rows | 3 |
| Review rows | 0 |
| Unparsed amounts | 0 |

## Reconciliation checkpoint

| Fund | Revenue with transfers | Expenditure with transfers | Net |
|---:|---:|---:|---:|
| 151 | 1,021,582 | 1,261,204 | -239,622 |

Matches the packet's own printed "Excess of Estimated Revenues & Other Sources Over/(Under) Estimated Expenditures" figure for FY 2026-27 (`(239,622)`) exactly.

## Subtotal-level reconciliation

    10 groups compared; 10 matched; 0 mismatched; 12 roll-up totals skipped

Every comparable Sub-Total/Total Expense in the fund matches exactly. The large roll-up-skip count reflects this fund's structure: revenue and each of seven debt-service divisions (Principal x3, Interest x3, Other Charges/Other Debt Service x2) each restate their own Sub-Total as an identical "Total Expense" line immediately after, plus a final "Total Debt Service" and "Total Estimated Expenditures"/"Total Estimated Revenues" roll-up at the end.

## Notes

Fund 151 is structured differently from prior funds: it has no single Personal Services/Employee Benefits table, but instead seven small division-level debt-service blocks (Principal and Interest, split across General Governmental, Highway, and Education Debt Service divisions, plus Other Charges/Other Debt Service), each headed by its own repeated "Fund Number: 151" / "Description:" / "Division:" / "Acct. No.:" block.

Three of the same **dotted-account-code** extraction gap seen in Fund 143 (`47114.`) recurred here, at smaller individual scale but with one significant exception:

- `602. JAIL Principal on Notes` (page 145) — **budget_26_27 = 470,000**, the entire General Governmental Principal Sub-Total. This is a critical correction: without it, that Sub-Total would have shown an expected value of 0 against a printed 470,000, and Fund 151's overall net would have been off by the same amount.
- `613. CRT Interest on Other Loans Payable` (page 146) and `613. HVAC Interest on Other Loans Payable` (page 147) — both have `budget_26_27 = 0` (fully retired/expired by FY 2026-27), so neither affects the reconciliation total, but both were added anyway to preserve their `actual_24_25` history ($8,413 and $412,929 respectively), consistent with the project's "never discard source text" principle.

All three were caught the same way: hand-summing each division's Sub-Total against its visible line items *before* writing any correction, confirming the gap matched the missing row's value exactly, then verifying with `apply-row-corrections --strict` (zero unmatched/ambiguous).

Two additional OCR artifacts were found but deliberately **not corrected**, since they don't affect the fund's `budget_26_27`-based reconciliation and aren't cleanly fixable:

- **Page 147 has two rows both labeled exactly `"Sub-Total"`** (Interest/Highway and Interest/Education Debt Service divisions, on the same page). One of them has an OCR-misread `budget_25_26` value (`410,000` printed where the single underlying line item reads `10,000` — the same "extra leading digit" pattern seen in the Fund 131 checkpoint). Because `corrections.py`'s row key is `(document_id, page_number, account, label)` with no `line_number` component, a `replace` correction targeting this specific row would match *both* same-page, same-label `Sub-Total` rows — exactly the "ambiguous extracted-row match" case the correction-matching safeguards (issue #4) are designed to catch and refuse, rather than risk silently applying the fix to the wrong one. Left uncorrected and documented here instead.
- **Page 148 has a `Sub-Total` line with a garbled `budget_25_26` field** (`i¢}` where `0` is expected) that fails `TOTAL_ROW_RE`'s match entirely and so isn't extracted as a row at all. This doesn't lose any information: the line is immediately followed by an identical `Total Expense` line that extracts cleanly and captures the same figures.

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
| 151 | Reconciled in this checkpoint |

## Next work

- Continue extraction with Fund 171 General Capital Projects, pages 150-152.
- Fund 172 (Community Development, pages 153-155) and Fund 202 (Nursing Home, pages 156-158) remain after that.
- The Investment Policy amendment (Resolution 2026-52) is separate document/policy-text analysis, not fund extraction -- tracked separately.
