# Project Milestones

This document defines practical milestones for the budget-audit project. As of 2026-07-04, v0.1 through v0.4 are complete; v0.5 (generalization) is the only milestone with open work, and none of it is yet scoped into a GitHub issue.

## v0.1 — Reconciled packet slice plus first report

Goal: demonstrate that scanned local-government budget packets can be converted into reconciled, reviewable data and then into useful public questions.

Scope:

- Weakley County Finance, Ways, and Means packet dated 2026-06-30.
- Reviewed funds: 101, 116, 122, 131, and 141.
- Current reviewed page range: pages 23-138.

Definition of done:

- [x] Funds 101, 116, 122, 131, and 141 reconcile to reviewed source totals.
- [x] Checkpoint docs exist for pages 23-85 and Fund 141 pages 86-138.
- [x] Local Fund 141 review CSV artifacts are committed or regenerable. (`review/weakley-fwm-2026-06-30/page_review_086_138.csv` and `manual_row_corrections_086_138.csv` are tracked.)
- [x] Subtotal-level reconciliation report exists. See issue #1 (closed).
- [x] First reviewed-funds report exists. See issue #2 (closed).
- [x] Methodology explains OCR, review metadata, correction overlays, and reconciliation limits. (`docs/methodology.md`)

Value produced:

- A reviewed, reproducible dataset slice.
- A neutral report that converts budget rows into material changes and review questions.
- A concrete demonstration that the workflow works on a difficult scanned school-budget fund.

**Status: complete.**

## v0.2 — Complete packet budget funds

Goal: extend the workflow beyond the current reviewed slice and cover the remaining budget funds in the packet.

Definition of done:

- [x] Continue extraction with Fund 143 starting on page 139. See issue #3 (closed).
- [x] Identify and reconcile each remaining fund range. (Funds 151, 171, 172, 202 -- issues #7/#8/#9, all closed.)
- [x] Add checkpoint docs for each major reviewed range. (One per fund under `docs/checkpoints/`.)
- [x] Produce an updated full-packet or near-full-packet summary. (`reports/weakley-fwm-2026-06-30.md` now covers all 10 funds.)
- [x] Track unreconciled or ambiguous funds explicitly. (None remain -- every fund reconciles to its own printed total; see `ROADMAP.md`'s reconciliation checkpoint table.)

Value produced:

- A broader public-budget dataset for the packet.
- A clearer picture of how budget decisions are distributed across funds.

**Status: complete.** All ten funds in the packet reconcile.

## v0.3 — Analysis outputs

Goal: move from reconciled data to structured intelligence.

Definition of done:

- [x] Compute budget-to-budget deltas.
- [x] Compute actual-to-budget deltas.
- [x] Add materiality thresholds. (`MaterialityThreshold` -- `min_absolute`/`min_percent`, `require_both` defaults `True` after real-data testing showed noise with "either".)
- [x] Identify one-dollar and zero-dollar placeholders. (`data_quality.py`'s `placeholder_amount` warning.)
- [x] Identify grant/program lines appearing, disappearing, or materially changing. (`grant_roll_on`/`grant_roll_off` categories -- coarse heuristic, see `docs/report-design.md` "Status".)
- [x] Generate neutral review questions with source page references. (Category-specific public-records question templates.)
- [x] Produce markdown reports under `reports/`. (`reports/weakley-fwm-2026-06-30.md` -- not under a `findings/` subdirectory as originally sketched, one report file per packet instead.)

Value produced:

- Reusable reporting that helps readers focus attention where the data says attention is warranted.

**Status: complete.**

## v0.4 — Reliability and reviewer ergonomics

Goal: reduce manual debugging time and improve trust in the workflow.

Definition of done:

- [x] Improve correction replacement matching. See issue #4 (closed).
- [x] Warn or fail when replacement corrections do not match extracted rows. (`unmatched_replacements`/`ambiguous_extracted_matches`, raises under `--strict`.)
- [ ] Add guardrails for stale page-review files and stale correction overlays. Not implemented -- there's no automated staleness check (e.g. mtime comparison) between a page-review/correction CSV and the row file it applies to; this is still a manual-discipline requirement, not a tooling one.
- [x] Add subtotal/group reconciliation tests based on known Fund 141 failure modes. (`tests/test_subtotal_reconcile.py`'s continuation-page-group tests cover the exact cross-page subtotal pattern Fund 141 exposed.)
- [x] Document reviewer workflow for adding corrections. (`docs/corrections.md`.)

Value produced:

- Faster review cycles.
- Fewer hidden correction failures.
- Better audit trail.

**Status: mostly complete.** The one open item (stale-file guardrails) is a real gap, not yet worth its own issue given it hasn't caused a problem in practice across 10 funds -- worth revisiting if a future contributor hits it.

## v0.5 — Generalization beyond one packet

Goal: make the toolkit usable across packets, fiscal years, and jurisdictions.

Definition of done:

- [ ] Add config-driven jurisdiction and packet profiles.
- [ ] Support multiple fiscal years.
- [ ] Add dashboard-ready exports.
- [x] Document raw public PDF storage policy. See issue #11 (closed) -- `docs/methodology.md` "Preserve".
- [ ] Add documentation for journalists and citizens.
- [ ] Consider a static-site output.

Value produced:

- A reusable local-government budget intelligence toolkit rather than a one-off extraction script.

**Status: not started beyond the storage-policy item.** This is `ROADMAP.md`'s Phase 7 and the only milestone with real open work -- none of it scoped into a GitHub issue yet.
