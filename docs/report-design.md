# Report Design

This document is the detailed specification for the Analysis and Report phases of the methodology (`docs/methodology.md`, steps 6-7). It governs tone, finding taxonomy, clustering, and report structure for any code that turns extracted/reconciled budget rows into human-facing findings.

## Core framing

**A machine-generated report is a review queue, not an audit finding.**

This project should be calm, procedural, and hard to push against. If everything is legitimate, the report helps officials explain the budget. If something is sloppy, it exposes process weaknesses. If something is genuinely wrong, it narrows the search space through ordinary public-records questions. The goal is structured curiosity with receipts — not an accusation engine.

Do not imply corruption. Do not use inflammatory language. Do not overstate machine-generated findings. Do not treat OCR output as authoritative.

**Do not use the words "fraud," "waste," "abuse," "suspicious," or "illegal" unless a human has verified evidence and explicitly asks for that language.**

Prefer:

- "needs explanation"
- "requires review"
- "unclear from the packet"
- "possible extraction issue"
- "public-records follow-up candidate"
- "does not reconcile in this extraction"

## Workflow model

1. Extract budget data from public packets.
2. Preserve source traceability: document name, page number, fund, department, account number, line description, fiscal-year columns, extracted values.
3. Reconcile extracted revenue, expense, and transfer totals against source totals where possible.
4. Flag data-quality problems **separately** from substantive budget questions.
5. Detect material changes by both absolute-dollar change and percentage change (a $500,000 change on a $2,000,000 base outranks a $5,000 change on a $1,000 base, even though its percentage is smaller).
6. Group related lines into clusters before producing human-facing findings.
7. Classify findings into review categories.
8. Generate neutral public-records questions for each cluster.
9. Keep a review status for each finding.

## Finding categories

- `data_quality` — OCR errors, corrupted labels, missing rows, duplicate labels, impossible values, $1 placeholders, bad account mapping.
- `reconciliation` — fund totals do not balance in extraction, transfer handling unclear, revenue/expense mismatch.
- `grant_roll_on` — new grant/program revenue or expense appears.
- `grant_roll_off` — prior grant/program revenue or expense drops to zero.
- `capital_project` — building improvements, equipment, construction, road/bridge projects, large one-time purchases.
- `personnel_change` — salaries, wages, overtime, benefits, FTE-related movement.
- `insurance_or_benefits` — medical insurance, liability insurance, building/content insurance, retirement, Social Security, Medicare.
- `contracted_services` — vendor-like, agency, nonprofit, public-agency, private-agency, or consulting/service lines.
- `allocation_change` — recipients or municipalities appear, disappear, or materially change.
- `public_records_candidate` — item likely worth requesting documentation for.
- `needs_human_review` — fallback when classification is uncertain.

## Review status lifecycle

`machine_generated` → `source_verified` → `reconciled_to_packet` → `question_drafted` → `records_requested` → `explanation_received` → `resolved` / `still_unclear` / `discarded_extraction_error`.

## Analytic features

**Absolute-dollar materiality alongside percentage materiality.** Rank and filter by absolute dollar change, percentage change, prior amount, proposed amount, and fund-size context — not percentage alone.

**Revenue/expense pairing detection.** Detect likely paired movements across revenue and expense lines, especially where prefixes, program codes, grant names, or amounts suggest related activity (e.g. State Aid Program revenue ↔ State Aid Projects expense; CRD/development revenue ↔ CRD Building Improvements; PDG Preschool Development Grant revenue ↔ PDG expense lines; ISM grant/program revenue ↔ ISM salaries/equipment/building lines; OPID revenue/allocation lines ↔ OPID recipient allocations). When a pair exists, classify as "paired program movement" and ask for the program documentation instead of treating each line as isolated.

**Clustering.** Group related findings by fund, department, account prefix/code, line-item prefix (OPID, ISM, PDG, 3STAR, DGA, SPED, TRN, THSO, etc.), semantic similarity of descriptions, revenue/expense relationship, capital-project relationship, or recipient/payee/allocation relationship — before producing findings. Example cluster summaries: "OPID allocation changes," "Highway State Aid and road-material increases," "School grant roll-on/roll-off," "Insurance and benefit cost shifts," "CRD development/building-improvement project," "Transportation equipment and bus/fuel-related changes."

**Data-quality warnings, kept separate from substantive findings.** Corrupted OCR labels, strange punctuation, misspellings, partial-word line descriptions, $1 placeholder values, zero-to-nonzero or nonzero-to-zero transitions that may reflect placeholders, duplicate labels with different pages/departments, impossible or unlikely account mappings, reconciliation gaps. A likely OCR artifact should never be allowed to read like a substantive allegation.

**Public-records question generation**, one set per cluster, specific enough to be useful and neutral enough to be defensible. Examples:

- "Please provide the grant award letter, approved budget amendment, spending plan, and reporting requirements for this program."
- "Please provide the project list, bid documents, contracts, and commission minutes associated with this line item."
- "Please explain whether this line represents one-time, recurring, restricted, pass-through, or reimbursement-based funding."
- "Please identify the department, program, recipient, or transfer associated with this increase."
- "Please provide recipient lists, award criteria, applications, scoring documents, memoranda of understanding, and deliverables for these allocations."
- "Please confirm whether the source packet itself balances or whether this difference reflects a packet-level imbalance."

## Report structure

1. Title
2. Generated date
3. Source packet
4. Scope (funds/pages included and not yet included)
5. Methodology note
6. Reconciliation summary
7. Data-quality warnings
8. Executive summary
9. Top clusters
10. Top absolute-dollar changes
11. Top percentage changes
12. Findings by category
13. Public-records question candidates
14. Items needing manual verification
15. Appendix: raw material changes

Prefer "top changes by absolute dollars" plus "top changes by percentage" over percentage-only rankings, and group findings into clusters so the reader sees patterns instead of hundreds of isolated deltas. The report should be useful to a county commissioner, local reporter, concerned citizen, or auditor.

## Data outputs

Maintain CSV/JSON structured outputs for extracted line items, reconciliations, findings, clusters, generated questions, and review statuses, in addition to the Markdown report. The human-facing report should be generated from structured data, not ad hoc text.

## Coding expectations

- Prefer small, testable functions.
- Add tests for any parser, reconciler, classifier, or clusterer.
- Do not silently swallow extraction anomalies.
- Keep raw extracted values and normalized values both.
- Preserve source references on every finding.
- Avoid hard-coding Weakley-specific logic outside of a county-specific config — support future counties/packets through configuration.
- Make materiality and other thresholds configurable.
- Keep methodology documented.
- Make uncertainty explicit in the data model (confidence levels, review status).

## Status

As of 2026-07-04, this spec's v2 (the "civic-intelligence review packet" restructure, issue #32) is implemented against all 10 reconciled funds (101/116/122/131/141/143/151/171/172/202). The v1 status (8-category taxonomy, prefix clustering, data-quality warnings, top changes) described in earlier revisions of this section is superseded by the notes below.

- **Finding taxonomy (v2)**: replaced the v1 8-category set with a fine-grained, account-number-first classifier (`classify.categorize_line_item`): `insurance_or_claims`, `benefits_or_payroll_burden`, `personnel`, `debt_service`, `grant_or_intergovernmental_revenue`, `capital_project`, `allocation_or_recipient_payment`, `travel`, `communication`, `maintenance_services`, `contracted_services`, `supplies_and_materials`, `needs_human_review`, plus two cross-cutting categories generated separately from fund-level/cluster-level signals rather than per-line-item classification: `whole_fund_structural_change` and `grant_funded_capital_project`. Account number is checked before any label regex specifically to fix a real bug: "Building & Contents Insurance" (account 502) was landing in `capital_project` under the v1 label-only heuristic just because the label contains "Building" -- account-first priority order now sends it to `insurance_or_claims` instead, and the same discipline separates "Medical Insurance" (a benefit, account 207) from "Liability Insurance" (a claims/risk-transfer line, account 506) even though both labels contain the word "insurance". `grant_roll_on`/`grant_roll_off` (v1) are retired as categories -- new/eliminated status is still tracked, just as the existing `status` attribute on a delta row rather than a separate category.
- **Review-status lifecycle**: unchanged from v1, `models.FindingStatus` (9 states); `machine_generated` is the only state any code currently sets.
- **Clustering**: unchanged core mechanism (fund + label-prefix grouping, `clusters.py`), now additionally tagged with a `cluster_type` (`debt_service`, `grant_funded_capital_project`, `grant_funded_program`, `allocation_program`, `personnel_or_benefits`, `general`) derived from the majority `classify.categorize_line_item` category among a cluster's member rows, plus a one-paragraph plain-English `narrative` field. Recipient-allocation as the majority category is checked before grant-revenue pairing, so a cluster like `OPID` (opioid settlement revenue funding named city/nonprofit recipients) resolves to `allocation_program`, not `grant_funded_program`, even though its revenue side is grant-classified. Validated against real clusters: `151-JAIL`/`151-USDA`/`151-HVAC`/`151-CRT` (debt), `101-OPID` (allocation), `101-CRD`/`101-ISIP` (grant-funded capital), `141-ABE`/`141-SUM`/`141-ISM`/`141-PDG`/`141-TRN` (grant-funded program, personnel-dominated). Semantic-similarity clustering is still not implemented.
- **Revenue/expense pairing detection**: the v1 shared-label-prefix mechanism (`is_paired`) is now supplemented by a fund-level detector (`structural_changes.detect_grant_funded_capital_pairs`) for pairs that share no common prefix at all -- the real motivating case is Fund 172's "Other State Grants - Connected Communities Facilities" revenue (+$1,443,340) moving alongside "Building Construction" expense (+$1,603,710), neither of which has a label prefix, so prefix-based clustering alone can't catch it. A comparable-magnitude check (smaller delta must be at least 20% of the larger, both must clear a $25,000 floor) keeps a small grant next to an unrelated large capital project from being flagged as connected.
- **Whole-fund structural change detection**: new (`structural_changes.detect_whole_fund_changes`) -- flags a fund whose revenue and expenditure both collapse from materially active levels to near zero (or the reverse) on the headline transition. Validated against Fund 202 Nursing Home (Patient Charges + Remittance of Revenue Collected both -> 0) and additionally caught Fund 171 General Capital Projects, whose ordinary line-item revenue/expenditure both zero out even though the fund's own reconcile file shows nonzero net -- a real signal that its remaining activity is transfer-only, worth its own review question rather than being silently absorbed into "the fund is smaller now."
- **Data-quality impact scoring**: new (`data_quality.data_quality_impact_score`) -- combines severity, confidence, dollar amount, and whether the row shows up in a top-dollar change or a priority-typed cluster into one score; warnings at or above `HIGH_IMPACT_THRESHOLD` surface in the report's main body, everything else moves to Appendix B. This is what keeps the ~40-75 routine `$1`-placeholder and manual-correction-dependency warnings per report from flooding the main body while still surfacing the handful (single digits, in this packet) that actually touch a number the report is putting in front of a reader.
- **Manual corrections**: new summary (`manual_corrections.py`) in the main body (total count, count by fund, count by action, high-impact-by-dollar-amount) with the full row-by-row table moved to Appendix C; any finding or priority area whose evidence depends on a corrected row now carries an explicit "verify correction metadata before relying on it" note.
- **Priority follow-up areas**: new (`priority_areas.py`) -- synthesizes a ranked, capped list (default 10) from whole-fund changes, fund-level grant/capital pairs, notable-typed clusters, and high-impact data-quality warnings, not from every individual finding. Reserves minimum slots for debt-service and allocation-program clusters so a handful of large grant/capital pairs can't crowd out smaller but still-important patterns on pure dollar magnitude alone, and dedupes a cluster-level `grant_funded_capital_project` against a fund-level pair for the same fund.
- **Public-records question generation**: category-specific templates (`questions.py`) matched to the new taxonomy (an insurance line no longer gets a bid-documents question); a section-level dedup (`questions.dedupe_questions`) means a question repeated across many findings in the same category renders once, not once per finding.
- **Reconciliation status naming**: `report.reconciliation_status()` replaces the old unconditional "reconciled" label (previously applied to every fund regardless of net) with `balanced_in_extraction` (net exactly zero), `extracted_with_gap` (nonzero net, small relative to fund size or under a flat dollar floor), or `needs_reconciliation_review` (nonzero net, large relative to fund size) -- the word "reconciled" is not used as a status value anywhere in the generated report.
- **Report structure and verbosity**: reordered into Title, Generated date/source, Scope and limitations, Reconciliation summary, Executive summary, Priority follow-up areas, Top clusters (with narrative), Top absolute-dollar changes, Top percentage changes, High-impact data-quality warnings, Public-records question candidates, Findings by category (3 representative examples per category, rest pointed to Appendix A), Appendix A (raw findings), Appendix B (all data-quality warnings), Appendix C (manual corrections), Appendix D (reconciliation detail), How to read this report. Three verbosity levels (`summary`/`standard`/`full`, default `standard`) control how much of this renders -- `summary` stops after Priority follow-up areas, `standard` adds everything through Public-records/Findings but omits appendices, `full` includes appendices. Still not implemented: a separate AI-written executive-summary section beyond the templated one (kept deliberately templated, not free-generated, to avoid drifting from the neutral-language posture).
- **Machine-readable outputs**: `findings.json`, `clusters.json`, `data_quality_warnings.json`, `manual_corrections.json`, `priority_areas.json` (CSV siblings), plus `questions.json` (the static template dict) and `reconciliation.json` (the summaries list) -- all written by `report_workflow.py` alongside the Markdown report.
- **Not yet implemented**: fund-size-relative materiality ranking (still absolute-dollar + percent only), config-driven multi-county jurisdiction profiles, semantic-similarity clustering, and automated staleness guardrails for page-review/correction files (see `docs/milestones.md` v0.4).
