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

As of 2026-07-02, this is the target design. The first analysis/report layer (`src/budget_audit/analyze.py`, `compensation.py`, `findings.py`, `report.py`) implements a subset: absolute+percent materiality, source references, a Markdown report with scope/reconciliation/findings sections, and only three finding categories (`delta`, `salary`, `reconciliation`) rather than the full taxonomy above. Clustering, pairing detection, public-records question generation, the review-status lifecycle, and the fuller report structure are not yet built.
