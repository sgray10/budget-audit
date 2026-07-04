# Manual Row Corrections

Manual correction files (`review/<document-id>/manual_row_corrections_*.csv`) let a human fix specific rows in an OCR-extracted budget row CSV, with the fix and its reason preserved alongside the original extracted data. Each row in a correction file has an `action` of `replace`, or `add`.

## `replace` vs `add`

**Use `replace` when a row *was* extracted but one or more fields are wrong** — the OCR misread an amount, garbled a label, or picked up a stray character. A `replace` correction is matched to its target extracted row by a **row key**: `(document_id, page_number, account, label)`. Matching is whitespace-normalized (leading/trailing whitespace stripped, internal whitespace runs collapsed) on all four fields, so an OCR-artifact extra space in a label won't break the match. Matching is **not** fuzzy beyond that — no edit-distance or partial matching is attempted, deliberately: a corrections tool that silently misapplies a fix to the wrong row is worse than a loud failure.

**Use `add` when a row was never extracted at all** — a skipped continuation page, a dotted account code the parser doesn't handle, a split-layout page. An `add` correction is an insertion, not a correction of an existing row; it doesn't need to match anything.

An `add` correction row may optionally include `row_type` and `category` columns to specify what kind of row is being inserted. Both default to `line_item`/`operating` for backward compatibility with correction files written before this option existed. **Set `row_type` explicitly whenever the row being added is a `transfer` or a `total`** — leaving it at the `line_item` default for those cases will make `reconcile_fund()` bucket a transfer as ordinary revenue/expenditure (silently wrong if the amount is nonzero), and will make `reconcile-subtotals` fail to close the total's own group, merging its line items into whatever the next real total row happens to be instead.

Example: adding a missing `Transfers In` row, page 106, fund 141:

```csv
document_id,page_number,line_number,action,fund_number,section_hint,row_type,category,account,label,actual_24_25,budget_25_26,actual_25_26,budget_26_27,reason,raw_line
weakley-fwm-2026-06-30,106,20,add,141,Fund 141 General Purpose School revenues,transfer,transfer,49800,Transfers In,,,,27000,row failed extraction,49800 Transfers In 27,000
```

**Use a last-resort balancing correction only when a reconciliation gap has been tracked down to a specific, understood cause that can't be cleanly expressed as a normal `add` or `replace` against a real source row.** This is an `add` with a small (often $1) delta amount and no real-world referent — a stopgap, not a fix, and a code smell to be minimized. Document the reason clearly enough that a future pass can replace it with a proper fix once the real gap is understood.

## Worked example: the Fund 141 page-106 case

`review/weakley-fwm-2026-06-30/manual_row_corrections_086_138.csv` contains a `replace` correction targeting `(page=106, account=790, label="Other Equipment")`. Page 106 was a split-layout continuation page the extractor doesn't handle, so no row with that key was ever extracted — the `replace` silently had nothing to match, and a second correction had to `add` a `-1` balancing row to fix the resulting $1 reconciliation overage, with its own `reason` column noting "replacement did not match row key" as an explicit workaround.

Under the current behavior, `apply_row_corrections()` detects and reports this case instead of letting it pass silently:

- By default (`strict=False`), an unmatched `replace` is recorded in the returned stats (`unmatched_replacements`) and printed as a console warning by the CLI — the pipeline still completes, since older correction files (like this one) may have known, already-worked-around gaps.
- With `--strict` (or `strict=True` when calling `apply_row_corrections()` directly), the same situation raises a `ValueError` — useful when authoring *new* correction files, to catch a bad row key immediately instead of discovering it via a downstream dollar mismatch.

## Other detected issues

- **Ambiguous extracted-row matches**: if a `replace` correction's key matches more than one extracted row, the correction is not applied to either (which one is intended is unclear) — reported in `ambiguous_extracted_matches`, and raises under `--strict`.
- **Duplicate correction keys**: if two `replace` corrections in the same file share a key, the last one wins (preserved for backward compatibility) but is reported in `ambiguous_correction_keys`. This is a real data-quality issue worth fixing in the correction file itself, but does **not** raise even under `--strict` — it's a known, deliberate exception, not a silent failure mode.

## Scope boundary

Row-key matching is whitespace-normalized only. Fuzzy or edit-distance matching (e.g. tolerating a misspelled label or a shifted account digit) is deliberately out of scope — see the reasoning above.
