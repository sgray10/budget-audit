# Data Model

This is the first-pass schema. It will evolve as real packet formats are ingested.

## Document

A source record such as a meeting packet, adopted budget, audit report, amendment, or public-records response.

| Field | Type | Notes |
|---|---:|---|
| document_id | string | Stable local id. |
| title | string | Human-readable title. |
| jurisdiction | string | Example: Weakley County, TN. |
| body | string | Example: Finance, Ways, and Means Committee. |
| meeting_date | date | If applicable. |
| fiscal_year | string | Example: FY 2026-27. |
| source_url | string | Public URL if available. |
| acquired_at | datetime | When obtained. |
| file_path | string | Local raw path. |
| sha256 | string | File integrity hash. |
| notes | string | Completeness, caveats, etc. |

## Page

| Field | Type | Notes |
|---|---:|---|
| document_id | string | Parent document. |
| page_number | integer | 1-based page number. |
| has_text_layer | boolean | Digital text available. |
| likely_table | boolean | Detection heuristic. |
| section_hint | string | Example: Fund 101 Revenue. |
| ocr_required | boolean | True for scanned/image pages. |
| extraction_status | string | pending, extracted, reviewed. |

## BudgetLineItem

| Field | Type | Notes |
|---|---:|---|
| line_item_id | string | Stable derived id. |
| document_id | string | Source document. |
| page_number | integer | Source page. |
| fund_number | string | Example: 101. |
| fund_name | string | Example: General Fund. |
| department_code | string | Optional. |
| department_name | string | Optional. |
| account_code | string | Object/account code. |
| account_name | string | Human-readable line item. |
| sub_account | string | Optional secondary code label. |
| fiscal_year | string | FY represented by value. |
| amount_type | string | actual, budget, proposed, amendment. |
| period_label | string | Example: Actual 24-25. |
| amount | decimal | Parsed numeric value. |
| raw_amount | string | Original text. |
| raw_row_text | string | Original extracted row. |
| extraction_method | string | pdf_text, table, ocr, manual. |
| confidence | decimal | 0.0 to 1.0. |
| review_status | string | extracted, normalized, needs_review, confirmed. |
| notes | string | Any caveat. |

## Amendment

| Field | Type | Notes |
|---|---:|---|
| amendment_id | string | Stable id. |
| resolution_number | string | Example: 2026-47. |
| fund_number | string | Fund affected. |
| fiscal_year | string | Fiscal year affected. |
| account_code | string | Optional. |
| account_name | string | Optional. |
| increase | decimal | Increase amount. |
| decrease | decimal | Decrease amount. |
| net_change | decimal | increase - decrease. |
| reason | string | If stated. |
| source_page | integer | Page number. |
| confidence | decimal | 0.0 to 1.0. |

## Finding

A finding can be benign, unclear, or concerning. Findings should not overstate evidence.

| Field | Type | Notes |
|---|---:|---|
| finding_id | string | Stable id. |
| title | string | Short label. |
| category | string | delta, reconciliation, salary, policy, governance, question. |
| severity | string | info, low, medium, high. |
| confidence | string | low, medium, high. |
| summary | string | Citizen-readable explanation. |
| evidence | string | Source references. |
| open_questions | string | What needs clarification. |
| status | string | draft, reviewed, published, closed. |

## Confidence guidance

- `high`: extracted directly from digital text/table and reconciled.
- `medium`: extracted cleanly but not reconciled or has formatting ambiguity.
- `low`: OCR/manual interpretation or unclear source structure.

## Design note

The schema intentionally separates extracted data from findings. Numbers should be reusable even when interpretations change.
