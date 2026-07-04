from __future__ import annotations

# Neutral, category-specific public-records question templates. Each
# category gets a question set that actually matches what that category of
# line item is -- an insurance line does not need a bid-documents question,
# a personnel line does not need a grant-award-letter question. Templates
# are deliberately requests for documentation, not assertions.
PUBLIC_RECORDS_QUESTIONS: dict[str, list[str]] = {
    "capital_project": [
        "Please provide the project scope, bid documents, vendor contracts, approved budget amendments, and commission minutes.",
        "Is this a one-time capital expenditure or part of a recurring capital program?",
    ],
    "grant_or_intergovernmental_revenue": [
        "Please provide the grant award letter, grant budget, match requirements, approved spending plan, and reporting requirements.",
        "Is this funding one-time, recurring, restricted, pass-through, or reimbursement-based?",
    ],
    "allocation_or_recipient_payment": [
        "What program authorizes these allocations, and who selected the recipients?",
        "Please provide recipient lists, eligibility criteria, applications, scoring documents, award letters, contracts/MOUs, and deliverables.",
        "Are these one-time or recurring allocations?",
    ],
    "debt_service": [
        "Please provide the debt schedule, note/loan documents, repayment schedule, purpose of borrowing, and commission approval minutes.",
        "Is this a one-time issuance, refinancing, or retirement of debt, or a recurring annual debt-service obligation?",
    ],
    "insurance_or_claims": [
        "Please provide premium assumptions, carrier/provider information, renewal documents, a claims history summary if available, and an explanation of any major change.",
    ],
    "benefits_or_payroll_burden": [
        "Please explain whether this change reflects a rate change, headcount change, plan change, or a reclassification between benefit categories.",
    ],
    "personnel": [
        "Does this line item represent one position or several?",
        "Please explain whether the change reflects new positions, reclassification, salary schedule changes, grant-funded positions, vacancies, or movement between departments.",
    ],
    "contracted_services": [
        "Please identify the contracted party, the contract term, and the procurement method used.",
        "Please provide the contract and any amendments associated with this line item.",
    ],
    "travel": [
        "Please explain the purpose and frequency of this travel and whether it is grant-funded, training-related, or routine departmental travel.",
    ],
    "communication": [
        "Please explain what drove this change -- a rate change, a new service, or a change in usage.",
    ],
    "maintenance_services": [
        "Please explain whether this reflects routine maintenance, a one-time repair, or a new maintenance agreement, and provide the vendor/agreement if available.",
    ],
    "supplies_and_materials": [
        "Please explain what drove this change -- price, quantity/usage, or a one-time purchase.",
    ],
    "needs_human_review": [
        "What explains this change or presence/absence of this line item?",
        "Is this recurring or one-time?",
    ],
    "grant_funded_capital_project": [
        "Please provide grant award documents, project scope, budget amendment, match requirements, contracts, bid documents, vendor list, project timeline, and commission approval minutes.",
    ],
    "whole_fund_structural_change": [
        "Does this fund remain active?",
        "Was this activity moved to another fund, transferred, closed, privatized, or otherwise reclassified?",
        "Please provide minutes, resolutions, contracts, or accounting notes explaining the change.",
    ],
    "reconciliation": [
        "Does the source document itself balance, or does the county packet show the same gap?",
        "Please confirm whether the source packet itself balances or whether this difference reflects a packet-level imbalance.",
    ],
    "data_quality": [
        "Please verify the source page and extracted values before using this row in public-facing analysis.",
    ],
}


def questions_for_category(category: str) -> list[str]:
    return PUBLIC_RECORDS_QUESTIONS.get(category, PUBLIC_RECORDS_QUESTIONS["needs_human_review"])


def dedupe_questions(questions: list[str]) -> list[str]:
    """Deduplicate while preserving first-seen order, so a section built from
    several findings doesn't repeat the same question string verbatim."""
    seen: set[str] = set()
    result: list[str] = []
    for question in questions:
        if question not in seen:
            seen.add(question)
            result.append(question)
    return result


__all__ = ["PUBLIC_RECORDS_QUESTIONS", "dedupe_questions", "questions_for_category"]
