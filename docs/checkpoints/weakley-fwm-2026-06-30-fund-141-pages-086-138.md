# Checkpoint: Weakley FWM 2026-06-30 Fund 141 pages 86-138

## Scope

Reviewed packet range: pages 86-138.

Covered fund:

- Fund 141 General Purpose School

Fund 141 begins on page 86. The next fund, Fund 143, begins on page 139, so this checkpoint treats pages 86-138 as the reviewed Fund 141 range.

## Reproducible command chain

    budget-audit render-pages data/raw/FWM-Meeting-Packet-6-30-26.pdf \
      --pages 86-138 \
      --out data/interim/rendered \
      --dpi 200

    budget-audit ocr-pages data/interim/rendered \
      --pages 86-138 \
      --out data/interim/ocr

    budget-audit run-reviewed-range data/interim/ocr \
      --pages 86-138 \
      --document-id weakley-fwm-2026-06-30 \
      --page-review review/weakley-fwm-2026-06-30/page_review_086_138.csv \
      --corrections review/weakley-fwm-2026-06-30/manual_row_corrections_086_138.csv \
      --out-dir data/processed \
      --funds 141

## Row counts

| Metric | Count |
|---|---:|
| Extracted OCR rows | 645 |
| Classified rows | 645 |
| Replaced rows | 6 |
| Added rows | 52 |
| Review rows | 7 |
| Unparsed amounts | 0 |

## Reconciliation checkpoint

| Fund | Revenue with transfers | Expenditure with transfers | Net |
|---:|---:|---:|---:|
| 141 | 48,156,476 | 48,154,424 | 2,052 |

## Notes

Fund 141 required a substantial manual correction overlay because the scanned school-budget pages include several OCR patterns that the row extractor does not yet handle automatically:

- split-layout continuation pages where account codes, labels, and amounts appear in separate OCR blocks;
- FTE/count values fused into amount columns;
- OCR artifacts in zero or small-dollar fields such as `ie)`, `~+`, `{SM`, and pipe-like characters;
- rows with dotted account codes or prefix artifacts that were skipped by the parser;
- one explicit balancing correction for a one-dollar overage where row replacement did not match the extracted row key.

The raw OCR is preserved separately from the manual correction overlay. The corrected output reconciles exactly to the Fund 141 summary totals.

## Current covered funds

The reviewed/reconciled packet coverage now includes:

| Fund | Status |
|---:|---|
| 101 | Reconciled in pages 23-85 checkpoint |
| 116 | Reconciled in pages 23-85 checkpoint |
| 122 | Reconciled in pages 23-85 checkpoint |
| 131 | Reconciled in pages 23-85 checkpoint |
| 141 | Reconciled in this checkpoint |

## Next work

- Commit or regenerate `page_review_086_138.csv` and `manual_row_corrections_086_138.csv` from local review artifacts.
- Improve correction replacement matching so one-dollar balancing rows are not needed.
- Add subtotal-level reconciliation to localize gaps without ad hoc scripts.
- Continue extraction with Fund 143 starting on page 139.
