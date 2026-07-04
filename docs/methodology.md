# Methodology

## Core principle

The project converts public financial documents into structured, traceable data. It should support investigation without becoming narrative-driven.

The workflow is:

```text
Acquire -> Preserve -> Extract -> Normalize -> Reconcile -> Analyze -> Report -> Review
```

## 1. Acquire

Collect source material from public sources or lawful records requests.

Minimum metadata:

- Document title
- Public body or department
- Meeting date or fiscal year
- Source URL or request origin
- Acquisition date
- File hash
- Notes on completeness

## 2. Preserve

Raw files should be immutable. Do not edit PDFs in place. Derived outputs go into `data/interim/` and `data/processed/`.

Recommended local layout:

```text
data/
  raw/
  interim/
  processed/
reports/
```

## 3. Extract

Extraction should preserve provenance.

Each extracted row should include:

- source document id
- source file path
- page number
- extraction method
- raw text
- parsed fields
- confidence
- review status

Preferred methods:

1. Text-layer extraction for digital PDFs.
2. Table extraction for structured PDF tables.
3. OCR fallback for scanned pages.
4. Manual correction only with explicit notes.

## 4. Normalize

Normalize records into stable fields:

- fund number
- fund name
- department code
- department name
- account/object code
- account/object name
- fiscal year
- amount type: actual, adopted budget, amended budget, proposed budget, amendment
- amount
- source page
- confidence

Never discard source text. Normalization should be reversible enough that a reviewer can see where the interpretation came from.

## 5. Reconcile

Reconciliation is the trust layer.

Examples:

- Row totals equal section totals.
- Fund revenue and expenditure totals match stated totals.
- Amendment increases/decreases net to the stated budget change.
- Fund balance changes reconcile against revenues, expenditures, and transfers.

Failed reconciliation is not proof of misconduct. It is a review item.

## 6. Analyze

See `docs/report-design.md` for the detailed finding taxonomy, clustering, pairing-detection, and public-records-question-generation spec that governs steps 6-7. A machine-generated report is a review queue, not an audit finding — see that document's tone and language rules before writing any finding-generation or report code.

Analysis should distinguish:

- factual findings
- calculations
- interpretations
- questions
- hypotheses

Useful analysis categories:

- material dollar changes
- material percentage changes
- recurring vs one-time changes
- salary and benefit trends
- debt service changes
- fund balance trends
- grant dependency
- transfers between funds
- aggregation that obscures individual line-item visibility

## 7. Report

Reports should be citizen-readable and source-linked.

Each claim should have:

- source document
- page number
- extracted value
- calculation, if any
- confidence level
- review notes, if needed

## 8. Review

Maintain a review queue. The goal is not to force certainty; the goal is to separate known facts from uncertain items.

Suggested review statuses:

- `extracted`
- `normalized`
- `reconciled`
- `needs_review`
- `confirmed`
- `superseded`

## Ethical posture

This project should be useful whether it finds:

- ordinary administrative messiness
- weak documentation
- structural budget problems
- unclear public reporting
- genuine irregularities

Do not imply intent from ambiguity alone. Ask better questions.
