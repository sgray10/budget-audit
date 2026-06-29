# Roadmap

## Phase 0 — Repository foundation

Goal: establish the project shape and analysis discipline.

- [x] Create repository scaffold.
- [x] Write mission and methodology docs.
- [x] Define initial data model.
- [ ] Add sample input packet manifest.
- [ ] Add first fixture PDF or redacted page examples if appropriate.
- [ ] Decide whether raw public PDFs should be committed, mirrored as releases, or stored externally.

## Phase 1 — Document inventory

Goal: know what we have before extracting anything.

- [ ] Build `inspect-pdf` command.
- [ ] Count pages.
- [ ] Detect text layer vs scanned image pages.
- [ ] Identify likely table pages.
- [ ] Compute file hash.
- [ ] Create a packet manifest with title, meeting date, funds included, and document sections.

Output: `data/processed/documents.csv` and `data/processed/pages.csv`.

## Phase 2 — Table extraction

Goal: get line-item tables out of PDFs with provenance.

- [ ] Support digital-PDF extraction with `pdfplumber`.
- [ ] Support OCR fallback for scanned pages.
- [ ] Preserve page number, extraction method, confidence, and raw row text.
- [ ] Export raw tables to CSV/JSONL.
- [ ] Add manual review status fields.

Output: `data/interim/tables/*.csv` and `data/interim/extracted_rows.jsonl`.

## Phase 3 — Budget normalization

Goal: convert extracted rows into analyzable records.

- [ ] Normalize fund numbers and names.
- [ ] Normalize account/object codes.
- [ ] Normalize departments and sub-departments.
- [ ] Parse amount columns such as `Actual 24-25`, `Budget 25-26`, `Actual 25-26`, `Budget 26-27`.
- [ ] Track missing, zero, negative, and parenthetical values.
- [ ] Preserve original row text.

Output: `data/processed/budget_line_items.csv`.

## Phase 4 — Reconciliation

Goal: make extraction trustworthy.

- [ ] Reconcile extracted subtotals against source totals where present.
- [ ] Flag row groups whose totals do not match.
- [ ] Record confidence levels and manual-review requirements.
- [ ] Produce a review queue.

Output: `reports/reconciliation.md` and `data/processed/review_queue.csv`.

## Phase 5 — Analysis

Goal: turn data into intelligence.

- [ ] Compute year-over-year deltas.
- [ ] Identify material changes by amount and percentage.
- [ ] Classify changes as recurring, one-time, unknown, or needs-review.
- [ ] Identify aggregated salary/compensation lines.
- [ ] Generate questions for public officials or journalists.
- [ ] Produce citizen-readable summaries.

Output: `reports/findings/*.md`.

## Phase 6 — Weakley County implementation

Goal: validate against real local documents.

- [ ] Ingest the 2026-06-30 Finance, Ways, and Means packet.
- [ ] Extract Fund 101 General Fund budget pages.
- [ ] Extract Fund 141 General Purpose School budget pages.
- [ ] Extract salary-related line items across funds.
- [ ] Compare investment policy versions.
- [ ] Build first public-facing summary.

## Phase 7 — Generalization

Goal: make the tool useful beyond one packet or one county.

- [ ] Add config-driven jurisdiction profiles.
- [ ] Support multiple fiscal years.
- [ ] Add dashboard-ready exports.
- [ ] Add documentation for journalists and citizens.
- [ ] Consider a static site output.
