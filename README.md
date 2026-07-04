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
  data/
    raw/           # committed -- public source packets, see "Data handling principles"
    interim/        # gitignored, regenerable
    processed/      # gitignored, regenerable
  docs/
    methodology.md
    data-model.md
    report-design.md
    backlog.md
    milestones.md
    value-model.md
    corrections.md
    weakley-county.md
    weakley-fwm-2026-06-30-workflow.md
    public-records-request-template.md
    checkpoints/
  reports/
    weakley-fwm-2026-06-30.md
  review/
    weakley-fwm-2026-06-30/
  src/budget_audit/
    __init__.py
    cli.py
    models.py
    render.py
    ocr.py
    ocr_table_rows.py
    ocr_reports.py
    row_classify.py
    enrich.py
    review.py
    corrections.py
    subtotal_reconcile.py
    consolidate.py
    workflow.py
    report_workflow.py
    analyze.py
    compensation.py
    clusters.py
    data_quality.py
    top_changes.py
    findings.py
    extract.py
    normalize.py
    reconcile.py
    summarize.py
    report.py
  tests/
    test_*.py
  examples/
    weakley_packet_manifest.example.yml
  pyproject.toml
  .gitignore
```

## Quick start

Install the package locally:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev,ocr]'
```

The current Weakley County workflow has two main stages.

First, produce reviewed/corrected rows for a page range:

```bash
budget-audit run-reviewed-range data/interim/ocr \
  --pages 23-85 \
  --document-id weakley-fwm-2026-06-30 \
  --page-review review/weakley-fwm-2026-06-30/page_review_023_085.csv \
  --corrections review/weakley-fwm-2026-06-30/manual_row_corrections_023_085.csv \
  --out-dir data/processed \
  --funds 101,116,122,131
```

Then consolidate reviewed ranges and generate the report:

```bash
budget-audit generate-report \
  --rows data/processed/ocr_table_rows_023_085_corrected.csv \
  --rows data/processed/ocr_table_rows_86_138_corrected.csv \
  --rows data/processed/ocr_table_rows_139_142_corrected.csv \
  --rows data/processed/ocr_table_rows_143_149_corrected.csv \
  --rows data/processed/ocr_table_rows_150_152_corrected.csv \
  --rows data/processed/ocr_table_rows_153_155_corrected.csv \
  --rows data/processed/ocr_table_rows_156_158_corrected.csv \
  --reconcile 101=data/processed/reconcile_fund_101_023_085.csv \
  --reconcile 116=data/processed/reconcile_fund_116_023_085.csv \
  --reconcile 122=data/processed/reconcile_fund_122_023_085.csv \
  --reconcile 131=data/processed/reconcile_fund_131_023_085_corrected.csv \
  --reconcile 141=data/processed/reconcile_fund_141_86_138.csv \
  --reconcile 143=data/processed/reconcile_fund_143_139_142.csv \
  --reconcile 151=data/processed/reconcile_fund_151_143_149.csv \
  --reconcile 171=data/processed/reconcile_fund_171_150_152.csv \
  --reconcile 172=data/processed/reconcile_fund_172_153_155.csv \
  --reconcile 202=data/processed/reconcile_fund_202_156_158.csv \
  --out-dir data/processed \
  --reports-dir reports
```

## Data handling principles

- Store original records unchanged under `data/raw/`. These are public government records and are committed to this repo so anyone can independently re-run extraction against the exact original -- see `docs/methodology.md` "Preserve" for the full storage policy.
- Do not commit sensitive or non-public records.
- Record document title, source URL or request origin, acquisition date, page number, and extraction method.
- Every derived number should be traceable back to a source page.
- Ambiguity should be preserved, not hidden.

## Current status

The Weakley County 2026-06-30 packet workflow has extracted and reconciled the budget pages for all ten funds in pages 23-158, and the analysis/report layer now implements the fuller `docs/report-design.md` taxonomy: an 8-category finding classification, dynamic label-prefix clustering with revenue/expense pairing detection, data-quality warnings separated from substantive findings, top absolute/percent change rankings, and category-specific public-records question templates. See `docs/report-design.md`'s "Status" section for exactly what's implemented vs. still deferred, and `ROADMAP.md` for the phase-by-phase picture. As of 2026-07-04, every tracked GitHub issue for this packet is closed; the next open work is Phase 7 (generalization beyond this one packet), not yet scoped into an issue.

## Current Weakley County OCR workflow

The current end-to-end OCR workflow for the Weakley County Finance, Ways, and Means packet is documented here:

- `docs/weakley-fwm-2026-06-30-workflow.md`

Current pipeline stages:

1. Render scanned PDF pages to images.
2. OCR rendered pages.
3. Extract likely budget table rows.
4. Enrich rows with page-review metadata.
5. Classify rows by row type and category.
6. Apply traceable manual corrections.
7. Summarize classified OCR rows by fund, section, and compensation category.
8. Reconcile fund totals and subtotal groups.
9. Build findings and render a Markdown report.

CI runs `pytest`, `ruff check .`, and `mypy .` on pushes and pull requests to `main`.
