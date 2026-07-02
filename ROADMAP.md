# Roadmap

Status key:

- `[x]` Done enough for the current Weakley packet workflow.
- `[~]` Partially implemented; useful but not yet generalized.
- `[ ]` Not started or still mostly future work.

## Phase 0 — Repository foundation

Goal: establish the project shape and analysis discipline.

- [x] Create repository scaffold.
- [x] Write mission and methodology docs.
- [x] Define initial data model.
- [x] Add sample input packet manifest.
- [~] Add first fixture PDF or redacted page examples if appropriate.
- [ ] Decide whether raw public PDFs should be committed, mirrored as releases, or stored externally.

## Phase 1 — Document inventory

Goal: know what we have before extracting anything.

- [x] Build `inspect-pdf` command.
- [x] Count pages.
- [x] Detect text layer vs scanned image pages.
- [x] Identify likely table pages.
- [x] Compute file hash.
- [~] Create a packet manifest with title, meeting date, funds included, and document sections.

Output: `data/processed/documents.csv` and `data/processed/pages.csv`.

## Phase 2 — Table extraction

Goal: get line-item tables out of PDFs with provenance.

- [~] Support digital-PDF extraction with `pdfplumber`.
- [x] Support OCR fallback for scanned pages.
- [x] Preserve page number, extraction method context, confidence metadata, and raw row text.
- [x] Export OCR-derived table rows to CSV.
- [x] Add manual review status fields and a review queue.
- [x] Add page-filtered OCR row extraction so a working range can be reproduced.
- [ ] Export normalized raw rows to JSONL.

Current output: `data/processed/ocr_table_rows_*.csv`.

## Phase 3 — Budget normalization

Goal: convert extracted rows into analyzable records.

- [x] Normalize/enrich fund numbers and names using page-review metadata.
- [~] Normalize account/object codes.
- [~] Normalize departments and sub-departments.
- [x] Parse amount columns such as `Actual 24-25`, `Budget 25-26`, `Actual 25-26`, `Budget 26-27`.
- [~] Track missing, zero, negative, and parenthetical values.
- [x] Preserve original row text.
- [x] Classify rows by row type and category.
- [x] Apply traceable manual row corrections.

Current output: classified/corrected OCR row CSVs.

## Phase 4 — Reconciliation

Goal: make extraction trustworthy.

- [~] Reconcile extracted subtotals against source totals where present.
- [~] Flag row groups whose totals do not match.
- [x] Record confidence levels and manual-review requirements.
- [x] Produce an OCR review queue.
- [x] Produce per-fund reconciliation outputs.
- [x] Support a correction overlay for OCR misses and misreads.
- [ ] Add subtotal-level reconciliation reports. See issue #1.
- [ ] Improve replacement matching for manual corrections. See issue #4.

Current output: `data/processed/reconcile_fund_*.csv` and `data/processed/ocr_review_queue*.csv`.

## Phase 5 — Analysis

Goal: turn data into intelligence.

- [ ] Compute year-over-year deltas.
- [ ] Identify material changes by amount and percentage.
- [ ] Classify changes as recurring, one-time, unknown, or needs-review.
- [~] Identify aggregated salary/compensation lines.
- [ ] Generate questions for public officials or journalists.
- [ ] Produce citizen-readable summaries. See issue #2.

Output: `reports/findings/*.md`.

## Phase 6 — Weakley County implementation

Goal: validate against real local documents.

- [x] Ingest the 2026-06-30 Finance, Ways, and Means packet locally.
- [x] Extract and reconcile Fund 101 General Fund budget pages.
- [x] Extract and reconcile Funds 116, 122, and 131 through the current reviewed range.
- [x] Extract and reconcile Fund 141 General Purpose School budget pages.
- [ ] Continue extraction with Fund 143 starting on page 139. See issue #3.
- [~] Extract salary-related line items across funds.
- [ ] Compare investment policy versions.
- [ ] Build first public-facing summary. See issue #2.

## Phase 7 — Generalization

Goal: make the tool useful beyond one packet or one county.

- [ ] Add config-driven jurisdiction profiles.
- [ ] Support multiple fiscal years.
- [ ] Add dashboard-ready exports.
- [ ] Add documentation for journalists and citizens.
- [ ] Consider a static site output.

## Current checkpoint — 2026-06-30 packet, pages 23-138

The current working slice covers the Weakley County Finance, Ways, and Means packet budget pages 23-138. The pipeline can render/OCR pages, extract OCR rows, enrich with page-review metadata, classify rows, apply manual corrections, create review queues, summarize, and reconcile selected funds.

Known validated reconciliation checkpoint:

| Fund | Status | Notes |
|---:|---|---|
| 101 | Reconciled in pages 23-85 checkpoint | Net after transfers: -4,407. |
| 116 | Reconciled in pages 23-85 checkpoint | Small planned use of fund balance. |
| 122 | Reconciled in pages 23-85 checkpoint | Small planned use of fund balance. |
| 131 | Reconciled after correction overlay | Revenue 7,909,610; expenditures 7,868,699; net 40,911. |
| 141 | Reconciled after correction overlay | Revenue with transfers 48,156,476; expenditures 48,154,424; net 2,052. |

Next best milestones:

1. Commit or regenerate Fund 141 local review artifacts if they should be repo-tracked.
2. Add subtotal-level reconciliation reports so mismatches are found automatically instead of by ad hoc scripts. See issue #1.
3. Generate the first reviewed-funds intelligence report for funds 101, 116, 122, 131, and 141. See issue #2.
4. Continue extraction/page-review metadata with Fund 143. See issue #3.
5. Improve correction replacement matching so balancing rows are not needed. See issue #4.
