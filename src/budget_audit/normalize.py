from __future__ import annotations

from decimal import Decimal, InvalidOperation
import re

_AMOUNT_RE = re.compile(r"^\(?\s*[$]?\s*[-+]?\d[\d,]*(?:\.\d+)?\s*\)?$")
_CODE_RE = re.compile(r"\b\d{5}\b")


def normalize_whitespace(value: str) -> str:
    """Collapse repeated whitespace and trim a string."""
    return " ".join(value.split())


def parse_amount(value: str | None) -> Decimal | None:
    """Parse common government-budget amount strings.

    Supports commas, dollar signs, negatives, and parenthetical negatives.
    Empty strings and obvious placeholders return None.
    """
    if value is None:
        return None

    text = value.strip()
    if not text or text in {"-", "—", "--", "N/A"}:
        return None

    is_parenthetical_negative = text.startswith("(") and text.endswith(")")
    cleaned = text.replace("$", "").replace(",", "").replace("(", "").replace(")", "").strip()

    if not _AMOUNT_RE.match(text):
        return None

    try:
        amount = Decimal(cleaned)
    except InvalidOperation:
        return None

    return -amount if is_parenthetical_negative else amount


def extract_account_code(text: str) -> str | None:
    """Return the first five-digit account/object code found in text."""
    match = _CODE_RE.search(text)
    return match.group(0) if match else None


def classify_amount_column(label: str) -> str:
    """Classify a budget column label into a broad amount type."""
    lowered = label.lower()
    if "actual" in lowered:
        return "actual"
    if "amend" in lowered:
        return "amendment"
    if "budget" in lowered:
        return "budget"
    if "proposed" in lowered:
        return "proposed"
    return "unknown"


def looks_salary_related(text: str) -> bool:
    """Heuristic for compensation-related line items."""
    lowered = text.lower()
    terms = [
        "salary",
        "salaries",
        "wage",
        "wages",
        "overtime",
        "retirement",
        "insurance",
        "social security",
        "medicare",
        "employee benefits",
        "payroll",
    ]
    return any(term in lowered for term in terms)
