# Project Backlog

GitHub issues are now available through the connector. This file remains as the repo-tracked milestone board and links to the live issues that track implementation work.

## Milestone: v0.1 reviewed packet workflow

Goal: make the reviewed Weakley packet range reproducible from OCR text through corrected reconciliation.

Status: **complete for the full packet, pages 23-158.** All ten funds (101, 116, 122, 131, 141, 143, 151, 171, 172, 202) reconcile to reviewed summary totals.

Done:

- Page-filtered OCR extraction, including total/subtotal lines (not just account rows).
- Page-review metadata enrichment.
- Row classification.
- OCR review queue.
- Row correction overlay, with whitespace-normalized matching and unmatched/ambiguous detection (`--strict`).
- Subtotal-level reconciliation (`reconcile-subtotals`).
- Reviewed-range workflow runner.
- Per-fund reconciliation.
- Checkpoint doc for pages 23-85.
- Checkpoint doc for Fund 141 pages 86-138.
- Checkpoint doc for Fund 143 pages 139-142.
- Checkpoint doc for Fund 151 pages 143-149.
- Checkpoint doc for Fund 171 pages 150-152.
- Checkpoint doc for Fund 172 pages 153-155.
- Checkpoint doc for Fund 202 pages 156-158 (last fund in the packet).

Remaining:

- [ ] Verify CI status for the checkpoint commits.
- [ ] Refresh README quick-start commands for the corrected workflow.
- [ ] Keep generated `data/` artifacts local unless explicitly promoted.
- [ ] Commit or regenerate local review CSV artifacts for Fund 141 if they should be repo-tracked.

## Active issues

Source of truth is GitHub issues; this table is a quick index. Update it when issues open/close.

| Issue | Priority | Purpose | Status |
|---:|---|---|---|
| #1 | High | Add subtotal-level reconciliation reports. | Closed -- implemented in #5 |
| #2 | High | Generate the first reviewed-funds intelligence report. | Closed -- implemented (commit 29031a7) |
| #3 | Medium | Continue extraction with Fund 143. | Closed -- implemented in #5 |
| #4 | Medium | Improve correction replacement matching. | Closed -- implemented in #5 |
| #7 | Medium | Extract and reconcile Fund 171 General Capital Projects (pages 150-152). | Closed -- implemented in #13 |
| #8 | Medium | Extract and reconcile Fund 172 Community Development (pages 153-155). | Closed -- implemented in #15 |
| #9 | Medium | Extract and reconcile Fund 202 Nursing Home (pages 156-158). | Closed -- implemented in #16. **All fund extraction now complete.** |
| #10 | Low | Diff investment policy amendment (Resolution 2026-52). | Implemented, PR pending -- closes on merge |
| #11 | Low | Decide raw public PDF storage policy. | Closed -- implemented in #28 |
| #12 | Medium | Adopt the report-design.md finding taxonomy and clustering in the analysis layer. | Closed -- implemented across #17/#18/#23/#24 (Codex) and #25 |
| #14 | Medium | apply_row_corrections' add action can't represent transfer/total row types. | Closed -- implemented in #26 |
| #20 | Medium | Add top absolute-dollar and percentage change report sections (sub-issue of #12). | Closed -- implemented in #17/#18/#23/#24 (Codex) |
| #21 | Medium | Cluster related findings before rendering public-facing report output (sub-issue of #12). | Closed -- implemented in #25 |
| #22 | Medium | Generate neutral public-records question candidates from report findings (sub-issue of #12). | Closed -- implemented in #25 |

## Backlog items

### Harden the reviewed-range workflow runner

The initial `run-reviewed-range` command now runs extraction, enrichment, classification, optional correction overlay, review queue, summary, and reconciliation for configured reviewed ranges.

Acceptance criteria:

- [x] Supports page range.
- [x] Supports page-review CSV.
- [x] Supports optional correction CSV.
- [x] Writes predictable output names.
- [x] Has unit tests for path planning and command behavior.
- [ ] Add documentation showing the preferred command path for reviewed ranges.
- [ ] Add guardrails for missing page-review metadata and stale correction files.

### Add subtotal-level reconciliation — issue #1

Current reconciliation is fund-level. Fund 141 showed why page/group subtotal reconciliation should be automated: OCR misses were localizable through page, continuation-page, department, and major-section totals.

Acceptance criteria:

- [ ] Extract subtotal and total lines from OCR text.
- [ ] Compare page/group line-item totals to source subtotal lines.
- [ ] Support continuation-page groups where totals appear on a later page.
- [ ] Output mismatch CSV.
- [ ] Include page number, section, expected, actual, difference, and confidence.

### Generate first reviewed-funds intelligence report — issue #2

Create a citizen-readable markdown report from reviewed funds 101, 116, 122, 131, and 141.

Acceptance criteria:

- [x] Summarize reconciled totals by fund.
- [x] Compute budget-to-budget deltas.
- [x] Compute actual-to-budget deltas.
- [x] Add materiality thresholds.
- [ ] Identify one-dollar and zero-dollar placeholders.
- [ ] Identify grant/program lines appearing, disappearing, or materially changing. (material deltas are flagged generally; grant/program-specific tagging not yet distinguished)
- [x] Generate neutral review questions, not accusations.
- [x] Preserve source page references.
- [x] Include methodology and limitations.

Implemented in `src/budget_audit/analyze.py`, `src/budget_audit/compensation.py`, `src/budget_audit/findings.py`, `src/budget_audit/report.py` (`analyze-deltas`, `analyze-compensation`, `build-findings`, `report`, and umbrella `generate-report` CLI commands). First checkpoint: 250 material deltas, 3 compensation flags, 5 reconciliation findings across funds 101/116/122/131/141 -- see `docs/weakley-fwm-2026-06-30-workflow.md`. Scope explicitly excludes funds 143+ (pages 139+, not yet extracted).

### Continue extraction with Fund 143 — issue #3

Fund 141 General Purpose School is reconciled. Fund 143 begins on page 139.

Acceptance criteria:

- [x] Identify the complete Fund 143 page range. (139-142; Fund 151 begins page 143)
- [x] Render/OCR the needed Fund 143 pages. (already covered by the full-packet OCR pass)
- [x] Create page-review metadata for Fund 143.
- [x] Extract/enrich/classify Fund 143 rows.
- [x] Reconcile revenues and expenditures to summary lines.
- [x] Add corrections only where source review justifies them. (1 dotted-account-code drop, 4 FTE-fused-amount rows, both hand-verified against source totals before correcting)
- [x] Add a checkpoint doc when reconciled.

Implemented: `review/weakley-fwm-2026-06-30/page_review_139_142.csv`, `manual_row_corrections_139_142.csv`. Fund 143 reconciles exactly (revenue=expenditure=3,621,955, net=0) and all 9 subtotal groups match with zero mismatches -- see `docs/checkpoints/weakley-fwm-2026-06-30-fund-143-pages-139-142.md`. Next: Fund 151 Debt Service, pages 143-149.

### Improve correction replacement matching — issue #4

Fund 141 required one balancing correction because replacement matching did not catch one row cleanly.

Acceptance criteria:

- [ ] Review the correction row-key strategy.
- [ ] Support replacement matching that tolerates OCR artifacts in non-target amount columns when page/account/label context is strong enough.
- [ ] Detect unmatched replacement corrections and fail or warn loudly.
- [ ] Include tests for successful replacement, failed replacement, and ambiguous replacement cases.
- [ ] Document when to use add vs replace vs balancing correction rows.

### Build compensation summary output

Use row classification and labels to summarize salary and benefit-related lines.

Acceptance criteria:

- [x] Produce compensation summary by fund.
- [x] Produce compensation summary by department/division where metadata supports it.
- [x] Preserve source page references.
- [x] Flag ambiguous compensation labels for review.

Implemented in `src/budget_audit/compensation.py` (`analyze-compensation` CLI command). Heuristic is coarse and explicitly low-confidence; see `docs/weakley-fwm-2026-06-30-workflow.md` "Analysis and report generation".

### Diff investment policy amendment (Resolution 2026-52) -- issue #10

Resolution 2026-52 amends the county investment policy. Pages 3-22 of the packet (front matter, never previously OCR'd for fund extraction) turned out to contain both the original policy (pages 8-14, stamped "ORIGINAL") and the amended policy (pages 15-22) -- and the amended copy is itself a redline, with substantively new/changed text printed in red ink in the source scan, distinguishing it from carried-over black text.

Acceptance criteria:

- [x] Locate the investment policy amendment pages in the packet.
- [x] Extract or transcribe the amended policy text with page provenance.
- [x] If a prior policy version is available, diff old vs new. (It was available in the same packet -- no external records request needed.)
- [x] Answer the open questions above where the source supports it, flag as needs_review where it doesn't.
- [x] Publish as a short citizen-readable note with source page references.

Implemented: `docs/checkpoints/weakley-fwm-2026-06-30-investment-policy-resolution-2026-52.md`. Summary of the real diff: the amendment (1) makes the investment committee's membership and the County Trustee's delegated day-to-day investment authority explicit (a November 18, 2024 committee vote), and (2) rewrites the authorized-investment-types section to quote TCA 5-8-301 through 5-8-303 directly, which along the way swaps "student loan marketing association" for "federal home loan mortgage corporation" in the eligible-issuer list and adds a maturity/population-based commercial-paper carve-out. Two of the four open questions (are bimonthly investment reports public; are they actually reconciled against policy) can't be answered from this packet alone and are flagged as public-records follow-up candidates.

### Decide raw public PDF storage policy -- issue #11

The project currently assumes raw PDFs live locally in `data/raw/` and are not committed.

Acceptance criteria:

- [x] Decide whether raw public packets are stored externally, attached as releases, or never mirrored. (Decision: committed directly under `data/raw/` in this repo -- these are public records, and committing them makes extraction independently verifiable.)
- [x] Document the policy in README or methodology docs.
- [x] Ensure `.gitignore` and docs match the policy.

Implemented: `data/raw/` removed from `.gitignore`, `data/raw/FWM-Meeting-Packet-6-30-26.pdf` committed, policy documented in `docs/methodology.md` "Preserve" and `README.md` "Data handling principles".
