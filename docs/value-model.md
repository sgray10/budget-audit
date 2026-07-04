# Value Model

Budget Audit creates value by turning public budget packet PDFs into reconciled, reviewable data and then into neutral review questions.

## What the current dataset can already support

All ten funds in the Weakley FWM 2026-06-30 packet are reviewed and reconciled, covering the entire budget-table page range (23-158):

- Fund 101 General Fund
- Fund 116 Solid Waste
- Fund 122 Drug Control
- Fund 131 Highway
- Fund 141 General Purpose School
- Fund 143 School Nutrition
- Fund 151 Debt Service
- Fund 171 General Capital Projects
- Fund 172 Community Development
- Fund 202 Nursing Home

Every fund reconciles to its own printed source total exactly -- see `ROADMAP.md`'s reconciliation checkpoint table for the full per-fund numbers. Fund 141 General Purpose School, the largest and most complex fund in the packet:

| Metric | Value |
|---|---:|
| Revenue with transfers | 48,156,476 |
| Expenditure with transfers | 48,154,424 |
| Net | 2,052 |

## Current outputs

All of the sections below are implemented and rendered in `reports/weakley-fwm-2026-06-30.md`, not just planned:

1. Reviewed scope and limitations.
2. Reconciled totals by fund.
3. Data-quality warnings, kept separate from substantive findings.
4. Top clusters (related line items grouped by fund + label prefix, with revenue/expense pairing flagged).
5. Largest absolute-dollar and percentage changes.
6. One-dollar and zero-dollar placeholder rows (as a data-quality warning).
7. Grant and program lines that appear, disappear, or materially change (`grant_roll_on`/`grant_roll_off` categories).
8. Neutral, category-specific public-records questions for public review.
9. Methodology and confidence notes.

See `docs/report-design.md` for the full spec and its "Status" section for what's implemented vs. deferred (semantic-similarity clustering, fund-size-relative materiality, multi-jurisdiction config).

## Public-facing posture

The report should present review questions rather than conclusions beyond the data.

Example framing:

> This line increased materially from the prior budget. Is this a recurring operational increase, a one-time project, grant-funded activity, or a reclassification?

## Product direction

The project can become:

- a local transparency tool for public packet review;
- a repeatable workflow for other counties and fiscal years;
- a reporting system that converts reconciled data into prioritized review questions.

The core promise is not automatic conclusions. The core promise is traceable extraction, reconciliation, and disciplined inquiry.
