# Project Backlog

GitHub issue creation was not available through the connector at the time this backlog was created, so these are recorded as repo-tracked backlog items.

## Milestone: v0.1 reviewed packet workflow

Goal: make the reviewed Weakley packet range reproducible from OCR text through corrected reconciliation.

Status: mostly complete for pages 23-85.

Done:

- Page-filtered OCR extraction.
- Page-review metadata enrichment.
- Row classification.
- OCR review queue.
- Row correction overlay.
- Per-fund reconciliation.
- Checkpoint doc for pages 23-85.

Remaining:

- [ ] Verify CI status for the checkpoint commits.
- [ ] Refresh README quick-start commands for the corrected workflow.
- [ ] Keep generated `data/` artifacts local unless explicitly promoted.

## Backlog items

### Add a single runner command for reviewed packet ranges

Create a command such as:

    budget-audit run-packet-workflow ...

It should run extraction, enrichment, classification, correction overlay, review queue, summary, and reconciliation for a configured page range.

Acceptance criteria:

- [ ] Supports page range.
- [ ] Supports page-review CSV.
- [ ] Supports optional correction CSV.
- [ ] Writes predictable output names.
- [ ] Has unit tests for path planning and command behavior.

### Add subtotal-level reconciliation

Current reconciliation is fund-level. Add page/group subtotal reconciliation so OCR misses are detected automatically.

Acceptance criteria:

- [ ] Extract subtotal and total lines from OCR text.
- [ ] Compare page/group line-item totals to source subtotal lines.
- [ ] Output mismatch CSV.
- [ ] Include page number, section, expected, actual, difference, and confidence.

### Extend extraction into Fund 141

Fund 141 General Purpose School begins on page 86.

Acceptance criteria:

- [ ] Render/OCR the needed Fund 141 page range.
- [ ] Create page-review metadata for Fund 141.
- [ ] Extract/enrich/classify Fund 141 rows.
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
