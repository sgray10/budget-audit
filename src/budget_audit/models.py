from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, Field


class ExtractionMethod(StrEnum):
    PDF_TEXT = "pdf_text"
    TABLE = "table"
    OCR = "ocr"
    MANUAL = "manual"


class ReviewStatus(StrEnum):
    PENDING = "pending"
    EXTRACTED = "extracted"
    NORMALIZED = "normalized"
    NEEDS_REVIEW = "needs_review"
    CONFIRMED = "confirmed"
    SUPERSEDED = "superseded"


class Document(BaseModel):
    document_id: str
    title: str
    jurisdiction: str
    body: str | None = None
    meeting_date: date | None = None
    fiscal_year: str | None = None
    source_url: str | None = None
    acquired_at: datetime | None = None
    file_path: Path
    sha256: str | None = None
    notes: str | None = None


class PageRecord(BaseModel):
    document_id: str
    page_number: int = Field(ge=1)
    has_text_layer: bool
    likely_table: bool = False
    section_hint: str | None = None
    ocr_required: bool = False
    extraction_status: ReviewStatus = ReviewStatus.PENDING


class BudgetLineItem(BaseModel):
    line_item_id: str
    document_id: str
    page_number: int = Field(ge=1)
    fund_number: str | None = None
    fund_name: str | None = None
    department_code: str | None = None
    department_name: str | None = None
    account_code: str | None = None
    account_name: str | None = None
    sub_account: str | None = None
    fiscal_year: str | None = None
    amount_type: str | None = None
    period_label: str | None = None
    amount: Decimal | None = None
    raw_amount: str | None = None
    raw_row_text: str
    extraction_method: ExtractionMethod
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    review_status: ReviewStatus = ReviewStatus.EXTRACTED
    notes: str | None = None


class Finding(BaseModel):
    finding_id: str
    title: str
    category: str
    severity: str = "info"
    confidence: str = "low"
    summary: str
    evidence: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    status: str = "draft"
