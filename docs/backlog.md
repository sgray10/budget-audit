# Project Backlog

GitHub issue creation was not available through the connector at the time this backlog was created, so these are recorded as repo-tracked backlog items.

## Milestone: v0.1 reviewed packet workflow

Goal: make the reviewed Weakley packet range reproducible from OCR text through corrected reconciliation.

Status: mostly complete for pages 23-138. Funds 101, 116, 122, 131, and 141 reconcile to reviewed summary totals.

Done:

- Page-filtered OCR extraction.
- Page-review metadata enrichment.
- Row classification.
- OCR review queue.
- Row correction overlay.
- Reviewed-range workflow runner.
- Per-fund reconciliation.
- Checkpoint doc for pages 23-85.
- Checkpoint doc for Fund 141 pages 86-138.

Remaining:

- [ ] Verify CI status for the checkpoint commits.
- [ ] Refresh README quick-start commands for the corrected workflow.
- [ ] Keep generated `data/` artifacts local unless explicitly promoted.
- [ ] Commit or regenerate local review CSV artifacts for Fund 141 if they should be repo-tracked.

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

### Add subtotal-level reconciliation

Current reconciliation is fund-level. Fund 141 showed why page/group subtotal reconciliation should be automated: OCR misses were localizable through page, continuation-page, department, and major-section totals.

Acceptance criteria:

- [ ] Extract subtotal and total lines from OCR text.
- [ ] Compare page/group line-item totals to source subtotal lines.
- [ ] Support continuation-page groups where totals appear on a later page.
- [ ] Output mismatch CSV.
- [ ] Include page number, section, expected, actual, difference, and confidence.

### Continue extraction with Fund 143

Fund 141 General Purpose School is reconciled. Fund 143 begins on page 139.

Acceptance criteria:

- [ ] Identify the complete Fund 143 page range.
- [ ] Render/OCR the needed Fund 143 pages.
- [ ] Create page-review metadata for Fund 143.
- [ ] Extract/enrich/classify Fund 143 rows.
- [ ] Reconcile revenues and expenditures to summary lines.
- [ ] Add corrections only where source review justifies them.

### Build compensation summary output

Use row classification and labels to summarize salary and benefit-related lines.

Acceptance criteria:

- [ ] Produce compensation summary by fund.
- [ ] Produce compensation summary by department/division where metadata supports it.
- [ ] Preserve source page references.
- [ ] Flag ambiguous compensation labels for review.

### Add analysis outputs

Begin turning normalized rows into intelligence.

Acceptance criteria:

- [ ] Compute budget-to-budget deltas.
- [ ] Compute actual-to-budget deltas.
- [ ] Add materiality thresholds.
- [ ] Generate review questions for large or unclear changes.
- [ ] Produce a citizen-readable markdown report.

### Decide raw public PDF storage policy

The project currently assumes raw PDFs live locally in `data/raw/` and are not committed.

Acceptance criteria:

- [ ] Decide whether raw public packets are stored externally, attached as releases, or never mirrored.
- [ ] Document the policy in README or methodology docs.
- [ ] Ensure `.gitignore` and docs match the policy.
