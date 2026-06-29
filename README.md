# Budget Audit

Budget Audit is a civic-data toolkit for turning messy local-government finance documents into structured, traceable, reviewable intelligence.

The initial target is Weakley County, Tennessee Finance, Ways, and Means packets and related budget documents. The larger goal is a repeatable workflow for county-level budget review, salary transparency, fund analysis, and anomaly detection.

## Mission

This project is not designed to prove a predetermined narrative. It is designed to make public financial data easier to inspect.

The operating posture is:

1. Acquire public records.
2. Preserve source provenance.
3. Extract structured data.
4. Normalize entities, funds, accounts, departments, and line items.
5. Reconcile totals against source documents.
6. Identify questions, anomalies, and unclear items.
7. Document confidence levels and assumptions.
8. Publish reproducible findings.

A good result may be `everything reconciles`. A good result may also be `this line item needs explanation`. The point is disciplined inquiry.

## Initial use cases

- Parse meeting packets and budget PDFs.
- Extract fund/account/department line items.
- Compare actuals, current budgets, proposed budgets, and amendments.
- Track salaries and compensation-related line items where legally/publicly available.
- Compare year-over-year changes.
- Flag material changes, unexplained deltas, and aggregation that prevents easy review.
- Produce citizen-readable summaries with links back to source pages.

## Repository layout

```text
budget-audit/
  README.md
  ROADMAP.md
  docs/
    methodology.md
    data-model.md
    weakley-county.md
    public-records-request-template.md
  src/budget_audit/
    __init__.py
    cli.py
    models.py
    extract.py
    normalize.py
    reconcile.py
    report.py
  tests/
    test_normalize.py
  examples/
    weakley_packet_manifest.example.yml
  pyproject.toml
  .gitignore
```

## Quick start

This is an early scaffold. The intended local workflow will be:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]

budget-audit init-project data/weakley
budget-audit inspect-pdf data/raw/FWM-Meeting-Packet-6-30-26.pdf
budget-audit extract-tables data/raw/FWM-Meeting-Packet-6-30-26.pdf --out data/interim/tables
budget-audit normalize data/interim/tables --out data/processed/line_items.csv
budget-audit reconcile data/processed/line_items.csv
budget-audit report data/processed/line_items.csv --out reports/weakley-fwm-2026-06-30.md
```

## Data handling principles

- Store original records unchanged under `data/raw/`.
- Do not commit sensitive or non-public records.
- Record document title, source URL or request origin, acquisition date, page number, and extraction method.
- Every derived number should be traceable back to a source page.
- Ambiguity should be preserved, not hidden.

## Current status

Initial repository scaffold. Core implementation is intentionally minimal until we validate source formats and the analysis workflow against real packets.
