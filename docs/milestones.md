# Project Milestones

This document defines practical milestones for the budget-audit project.

## v0.1 — Reconciled packet slice plus first report

Goal: demonstrate that scanned local-government budget packets can be converted into reconciled, reviewable data and then into useful public questions.

Scope:

- Weakley County Finance, Ways, and Means packet dated 2026-06-30.
- Reviewed funds: 101, 116, 122, 131, and 141.
- Current reviewed page range: pages 23-138.

Definition of done:

- [x] Funds 101, 116, 122, 131, and 141 reconcile to reviewed source totals.
- [x] Checkpoint docs exist for pages 23-85 and Fund 141 pages 86-138.
- [ ] Local Fund 141 review CSV artifacts are committed or regenerable.
- [ ] Subtotal-level reconciliation report exists. See issue #1.
- [ ] First reviewed-funds report exists. See issue #2.
- [ ] Methodology explains OCR, review metadata, correction overlays, and reconciliation limits.

Value produced:

- A reviewed, reproducible dataset slice.
- A neutral report that converts budget rows into material changes and review questions.
- A concrete demonstration that the workflow works on a difficult scanned school-budget fund.

## v0.2 — Complete packet budget funds

Goal: extend the workflow beyond the current reviewed slice and cover the remaining budget funds in the packet.

Definition of done:

- [ ] Continue extraction with Fund 143 starting on page 139. See issue #3.
- [ ] Identify and reconcile each remaining fund range.
- [ ] Add checkpoint docs for each major reviewed range.
- [ ] Produce an updated full-packet or near-full-packet summary.
- [ ] Track unreconciled or ambiguous funds explicitly.

Value produced:

- A broader public-budget dataset for the packet.
- A clearer picture of how budget decisions are distributed across funds.

## v0.3 — Analysis outputs

Goal: move from reconciled data to structured intelligence.

Definition of done:

- [ ] Compute budget-to-budget deltas.
- [ ] Compute actual-to-budget deltas.
- [ ] Add materiality thresholds.
- [ ] Identify one-dollar and zero-dollar placeholders.
- [ ] Identify grant/program lines appearing, disappearing, or materially changing.
- [ ] Generate neutral review questions with source page references.
- [ ] Produce markdown reports under `reports/findings/`.

Value produced:

- Reusable reporting that helps readers focus attention where the data says attention is warranted.

## v0.4 — Reliability and reviewer ergonomics

Goal: reduce manual debugging time and improve trust in the workflow.

Definition of done:

- [ ] Improve correction replacement matching. See issue #4.
- [ ] Warn or fail when replacement corrections do not match extracted rows.
- [ ] Add guardrails for stale page-review files and stale correction overlays.
- [ ] Add subtotal/group reconciliation tests based on known Fund 141 failure modes.
- [ ] Document reviewer workflow for adding corrections.

Value produced:

- Faster review cycles.
- Fewer hidden correction failures.
- Better audit trail.

## v0.5 — Generalization beyond one packet

Goal: make the toolkit usable across packets, fiscal years, and jurisdictions.

Definition of done:

- [ ] Add config-driven jurisdiction and packet profiles.
- [ ] Support multiple fiscal years.
- [ ] Add dashboard-ready exports.
- [ ] Document raw public PDF storage policy.
- [ ] Add documentation for journalists and citizens.
- [ ] Consider a static-site output.

Value produced:

- A reusable local-government budget intelligence toolkit rather than a one-off extraction script.
