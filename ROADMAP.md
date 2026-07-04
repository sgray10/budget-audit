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
- [x] Decide whether raw public PDFs should be committed, mirrored as releases, or stored externally. Decision: committed directly under `data/raw/` -- see issue #11 and `docs/methodology.md` "Preserve".

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

- [x] Reconcile extracted subtotals against source totals where present. See issue #1.
- [x] Flag row groups whose totals do not match.
- [x] Record confidence levels and manual-review requirements.
- [x] Produce an OCR review queue.
- [x] Produce per-fund reconciliation outputs.
- [x] Support a correction overlay for OCR misses and misreads.
- [x] Add subtotal-level reconciliation reports. See issue #1 (closed).
- [x] Improve replacement matching for manual corrections. See issue #4 (closed; fuzzy/edit-distance tolerance was explicitly decided against, not implemented -- see `docs/corrections.md` "Scope boundary").

Current output: `data/processed/reconcile_fund_*.csv` and `data/processed/ocr_review_queue*.csv`.

**Phase 4 is complete** for this packet.

## Phase 5 — Analysis

Goal: turn data into intelligence.

- [x] Compute year-over-year deltas.
- [x] Identify material changes by amount and percentage.
- [x] Classify changes as recurring, one-time, unknown, or needs-review. (8-category taxonomy: `grant_roll_on`, `grant_roll_off`, `capital_project`, `contracted_services`, `allocation_change`, `personnel_change`, `needs_human_review`, `reconciliation`.)
- [x] Identify aggregated salary/compensation lines.
- [x] Generate questions for public officials or journalists. (category-specific public-records question templates.)
- [x] Produce citizen-readable summaries. See issue #2 (closed).

Output: `reports/weakley-fwm-2026-06-30.md`.

**Phase 5 is complete** for this packet, including the fuller `docs/report-design.md` taxonomy adopted in issue #12: dynamic label-prefix clustering with revenue/expense pairing detection, a `FindingStatus` review lifecycle, data-quality warnings separated from substantive findings, and top absolute/percent change rankings. See `docs/report-design.md`'s own "Status" section for exactly what's implemented vs. explicitly deferred (semantic-similarity clustering, fund-size-relative materiality, config-driven jurisdiction profiles, an AI-written executive summary).

## Phase 6 — Weakley County implementation

Goal: validate against real local documents.

- [x] Ingest the 2026-06-30 Finance, Ways, and Means packet locally.
- [x] Extract and reconcile Fund 101 General Fund budget pages.
- [x] Extract and reconcile Funds 116, 122, and 131 through the current reviewed range.
- [x] Extract and reconcile Fund 141 General Purpose School budget pages.
- [x] Continue extraction with Fund 143 (pages 139-142). See issue #3.
- [x] Continue extraction with Fund 151 Debt Service (pages 143-149).
- [x] Continue extraction with Fund 171 General Capital Projects (pages 150-152). See issue #7.
- [x] Continue extraction with Fund 172 Community Development (pages 153-155). See issue #8.
- [x] Continue extraction with Fund 202 Nursing Home (pages 156-158). See issue #9. **All funds in the packet are extracted and reconciled.**
- [x] Extract salary-related line items across funds.
- [x] Compare investment policy versions. See issue #10 (closed) -- `docs/checkpoints/weakley-fwm-2026-06-30-investment-policy-resolution-2026-52.md`.
- [x] Build first public-facing summary. See issue #2 (closed).

**Phase 6 is complete** for this packet: all 10 funds, the full analysis/report layer, and the one non-fund policy-text question (Resolution 2026-52) are done.

## Phase 7 — Generalization

Goal: make the tool useful beyond one packet or one county.

- [ ] Add config-driven jurisdiction profiles.
- [ ] Support multiple fiscal years.
- [ ] Add dashboard-ready exports.
- [ ] Add documentation for journalists and citizens.
- [ ] Consider a static site output.

This is the next open frontier -- no issues are currently filed against it. Before starting, decide whether the near-term goal is a second real jurisdiction/packet (stress-tests generalization against real data, same discipline as Phase 6) or tooling/generalization work in the abstract (config schema, multi-year support) without a second real dataset to validate against yet.

## Current checkpoint — 2026-06-30 packet, pages 23-158 (full packet)

**Every phase through Phase 6 is complete for this packet.** All ten funds (101, 116, 122, 131, 141, 143, 151, 171, 172, 202) are extracted, reviewed, corrected, and reconciled across the full budget-table range (pages 23-158). The pipeline renders/OCRs pages, extracts OCR rows (including total/subtotal lines), enriches with page-review metadata, classifies rows, applies manual corrections (whitespace-normalized matching, unmatched/ambiguous detection), builds review queues, summarizes, reconciles funds and subtotal groups, clusters related line items, flags data-quality issues, ranks top changes, classifies findings into an 8-category taxonomy, generates public-records questions, and renders a full Markdown report (`reports/weakley-fwm-2026-06-30.md`).

The one non-fund-extraction question in scope for this packet -- diffing the Resolution 2026-52 investment policy amendment -- is also done (issue #10).

Known validated reconciliation checkpoint:

| Fund | Status | Notes |
|---:|---|---|
| 101 | Reconciled in pages 23-85 checkpoint | Net after transfers: -4,407. |
| 116 | Reconciled in pages 23-85 checkpoint | Small planned use of fund balance. |
| 122 | Reconciled in pages 23-85 checkpoint | Small planned use of fund balance. |
| 131 | Reconciled after correction overlay | Revenue 7,909,610; expenditures 7,868,699; net 40,911. |
| 141 | Reconciled after correction overlay | Revenue with transfers 48,156,476; expenditures 48,154,424; net 2,052. |
| 143 | Reconciled after correction overlay | Revenue 3,621,955; expenditures 3,621,955; net 0 (exactly balanced budget). |
| 151 | Reconciled after correction overlay | Revenue 1,021,582; expenditures 1,261,204; net -239,622 (matches packet's own printed deficit exactly). |
| 171 | Reconciled, no corrections needed | Revenue 0; expenditures 37,524; net -37,524 (matches packet's own printed deficit exactly). |
| 172 | Reconciled after correction overlay | Revenue 1,579,857; expenditures 1,755,396; net -175,539 (matches packet's own printed deficit exactly). Worst OCR quality of any fund so far; motivated issue #14 (corrections.py add-action row_type limitation, since closed). |
| 202 | Reconciled after correction overlay | Revenue 0; expenditures 0; net 0 -- entirely zeroed-out FY 2026-27 budget (fund appears wound down). |

**No issues are currently open.** Next best milestones are all Phase 7 (generalization) work, and none has been scoped into a concrete issue yet -- see that phase's note above before starting.
