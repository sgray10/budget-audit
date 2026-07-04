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

As of 2026-07-04, most of this spec is implemented against all 10 reconciled funds (101/116/122/131/141/143/151/171/172/202):

- **Finding taxonomy**: expanded from 3 categories to 8 -- `grant_roll_on`, `grant_roll_off`, `capital_project`, `contracted_services`, `allocation_change`, `personnel_change`, `needs_human_review`, `reconciliation` -- assigned by a coarse, documented heuristic (`findings._categorize_delta`), consistent with `compensation.py`'s existing low-confidence-heuristic posture. `insurance_or_benefits` is deliberately not split out from `personnel_change` -- the spec's own descriptions overlap ("personnel_change" explicitly includes benefits) -- and `grant_roll_on`/`grant_roll_off` only fire on new/eliminated lines whose label contains "grant"; less literal grant naming won't be caught.
- **Review-status lifecycle**: implemented as `models.FindingStatus` (9 states); `machine_generated` is the only state any code currently sets -- everything past that is a human reviewer's call, not automated.
- **Clustering**: implemented (`clusters.py`) as fund + label-prefix grouping (prefixes detected dynamically, not from a fixed list -- real data has dozens: `BONUS`, `ISM`, `OPID`, `PDG`, `SPED`, `TRN`, `THSO`, `DGA`, and more). Semantic-similarity clustering is not implemented.
- **Revenue/expense pairing detection**: implemented as a byproduct of clustering (`is_paired` flag when a cluster has nonzero totals on both sides), validated against the real `OPID` (Opioid Settlement Funds) case -- appears as both a revenue line and named-recipient expenditure allocations. Not implemented as a distinct semantic match (e.g. matching "State Aid Program" revenue to "State Aid Projects" expense by name similarity) beyond shared label prefix.
- **Data-quality warnings**: implemented (`data_quality.py`, built independently of this plan) as a self-contained module operating on the consolidated rows directly -- manual-correction dependency, OCR-artifact characters, missing context, unparsed amounts, $1 placeholders -- rendered in its own report section, separate from substantive findings.
- **Public-records question generation**: implemented as static per-category templates (`findings.PUBLIC_RECORDS_QUESTIONS`), not per-cluster dynamic generation; rendered as its own report section (categories with a template only).
- **Report structure**: implemented -- Scope, Reconciliation summary, Data-quality warnings, Top clusters, Top absolute-dollar changes, Top percentage changes (with a $5,000 floor before percent-ranking, avoiding tiny-baseline noise), Findings by category, Public-records question candidates, How to read this report. Not implemented: a separate AI-written executive-summary section (Scope + Reconciliation summary serve that role instead, to avoid drifting from the neutral-language posture) and a full raw-deltas appendix (1600+ rows -- the CSV outputs serve this purpose instead of embedding them in Markdown).
- **Not yet implemented**: fund-size-relative materiality ranking (still absolute-dollar + percent only) and config-driven multi-county jurisdiction profiles.
