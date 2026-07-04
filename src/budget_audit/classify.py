from __future__ import annotations

import re

# Fine-grained line-item categorization, replacing findings.py's old flat
# {delta, salary, reconciliation} split and its account-blind label regexes.
# Account number is checked first wherever a reliable range exists -- it does
# not depend on OCR getting a label's wording exactly right, and it is what
# actually prevents the "Building & Contents Insurance" bug: account 502 is
# checked (and matched) before any capital/"building" pattern gets a chance
# to run. Label regexes remain as a fallback for accounts an OCR pass
# dropped or an account the fund doesn't use.
#
# Every account range and every regex below was checked against the real
# consolidated Weakley dataset (data/processed/reviewed_funds_rows.csv)
# before being written -- see the account/label samples pulled during this
# feature's design for the specific rows that motivated each range.

CATEGORY_ORDER = [
    "insurance_or_claims",
    "benefits_or_payroll_burden",
    "personnel",
    "debt_service",
    "grant_or_intergovernmental_revenue",
    "capital_project",
    "allocation_or_recipient_payment",
    "travel",
    "communication",
    "maintenance_services",
    "contracted_services",
    "supplies_and_materials",
    "needs_human_review",
]

# --- Account-number ranges -----------------------------------------------
# Accounts confirmed in real data: 502 Building & Contents Insurance, 503
# Student Accident Insurance, 506 Liability Insurance, 511 Vehicle
# Insurance, 513 Workers'/Workman's Compensation Insurance, 515 Damage
# Claims/Liability Claim, 516 Self-Insured Claims.
INSURANCE_ACCOUNTS = {502, 503, 506, 511, 513, 515, 516}
# 201 Social Security, 204 State Retirement, 205 Employee & Dependent
# Insurance, 207 Medical Insurance, 208 Dental Insurance, 212 Medicare
# Liability. 210/217 included per spec though not observed in this packet.
BENEFITS_ACCOUNTS = {201, 204, 205, 207, 208, 210, 212, 217}
PERSONNEL_ACCOUNT_RANGE = (105, 199)
# 602 Principal on Notes/Other Loans, 613 Interest on Other Loans Payable,
# 699 Other Debt Service -- all observed in Fund 151.
DEBT_SERVICE_ACCOUNT_RANGE = (600, 699)
GRANT_REVENUE_ACCOUNT_RANGE = (46000, 47999)
CAPITAL_ACCOUNT_RANGE = (700, 799)
SUPPLIES_ACCOUNT_RANGE = (400, 499)
CONTRACTED_ACCOUNT_RANGE = (300, 399)
# Account 316 is Fund 101's outside-agency/contribution line -- named cities,
# authorities, nonprofits, and civic organizations (City of Dresden, Martin
# Housing Authority, West Tennessee United Way, Chamber of Commerce, Dolly
# Parton Reading Railroad, and more). The account itself is a more reliable
# signal than trying to pattern-match every possible recipient name.
RECIPIENT_ACCOUNT = 316

# --- Label regexes (fallback, or to pick a 300s sub-category) ------------
# BENEFITS_RE's insurance phrases (medical/dental/employee-dependent) are
# checked before the generic INSURANCE_RE fallback below -- both categories
# legitimately contain the word "insurance" (an employee's medical insurance
# is a benefit; a county building's insurance is a claims/risk-transfer
# line), so word-only matching can't tell them apart. Account number
# resolves the real ambiguity in categorize_line_item(); these label
# regexes only matter when the account itself is missing or unrecognized.
BENEFITS_RE = re.compile(
    r"social security|retirement|medicare|unemployment|hybrid stabilization"
    r"|medical insurance|dental insurance|employee.*insurance|dependent insurance",
    re.IGNORECASE,
)
INSURANCE_RE = re.compile(r"insur|liability claim|self-insured claim", re.IGNORECASE)
TRAVEL_RE = re.compile(r"\btravel\b", re.IGNORECASE)
COMMUNICATION_RE = re.compile(
    r"communication|postal|internet connectivity|telephone", re.IGNORECASE
)
MAINTENANCE_RE = re.compile(r"maintenance|maintenance agreement", re.IGNORECASE)
RECIPIENT_LABEL_RE = re.compile(
    r"^(city of|town of|county of)\b|\bllc\b|\binc\.?\b|\bcoalition\b|\bauthority\b"
    r"|\bhousing\b|\bagency\b|\bunited way\b|\bnonprofit\b",
    re.IGNORECASE,
)


def _account_int(account: str) -> int | None:
    stripped = account.strip()
    return int(stripped) if stripped.isdigit() else None


def _in_range(value: int | None, bounds: tuple[int, int]) -> bool:
    return value is not None and bounds[0] <= value <= bounds[1]


def categorize_line_item(account: str, label: str, budget_side: str) -> str:
    """Assign one category to a line item, checked in a fixed priority order.

    Account number is authoritative wherever a reliable range/set exists;
    label regexes are checked in the same tier as their account signal (not
    after it), so a label match can't be preempted by a *later*, broader
    tier -- this is exactly what keeps "Building & Contents Insurance"
    (account 502) out of capital_project, since insurance is tier 1 and
    capital_project is a later tier regardless of the word "Building".

    Within tier 1, exact account membership is checked before either label
    regex, and the benefits-specific label regex before the generic
    insurance one: "Medical Insurance" at a benefits account (207) must
    resolve to benefits_or_payroll_burden, not insurance_or_claims, even
    though both categories' labels legitimately contain the word "insurance".
    """
    acct = _account_int(account)

    if acct in INSURANCE_ACCOUNTS:
        return "insurance_or_claims"
    if acct in BENEFITS_ACCOUNTS:
        return "benefits_or_payroll_burden"
    if BENEFITS_RE.search(label):
        return "benefits_or_payroll_burden"
    if INSURANCE_RE.search(label):
        return "insurance_or_claims"

    if _in_range(acct, PERSONNEL_ACCOUNT_RANGE):
        return "personnel"

    if _in_range(acct, DEBT_SERVICE_ACCOUNT_RANGE):
        return "debt_service"

    if budget_side == "revenue" and _in_range(acct, GRANT_REVENUE_ACCOUNT_RANGE):
        return "grant_or_intergovernmental_revenue"

    if _in_range(acct, CAPITAL_ACCOUNT_RANGE):
        return "capital_project"

    if acct == RECIPIENT_ACCOUNT or RECIPIENT_LABEL_RE.search(label):
        return "allocation_or_recipient_payment"

    if _in_range(acct, CONTRACTED_ACCOUNT_RANGE):
        if TRAVEL_RE.search(label):
            return "travel"
        if COMMUNICATION_RE.search(label):
            return "communication"
        if MAINTENANCE_RE.search(label):
            return "maintenance_services"
        return "contracted_services"

    if _in_range(acct, SUPPLIES_ACCOUNT_RANGE):
        return "supplies_and_materials"

    return "needs_human_review"


__all__ = ["CATEGORY_ORDER", "categorize_line_item"]
