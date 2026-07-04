from budget_audit.classify import categorize_line_item


def test_insurance_wins_over_capital_project_despite_building_in_label() -> None:
    """The motivating bug: 'Building & Contents Insurance' (account 502) must
    not land in capital_project just because the label contains 'Building'.
    """
    assert categorize_line_item("502", "Building & Contents Insurance", "expenditure") == "insurance_or_claims"


def test_insurance_accounts_and_label_fallback() -> None:
    assert categorize_line_item("506", "Liability Insurance", "expenditure") == "insurance_or_claims"
    assert categorize_line_item("513", "Workman's Compensation Insurance", "expenditure") == "insurance_or_claims"
    assert categorize_line_item("515", "Damage Claims", "expenditure") == "insurance_or_claims"
    assert categorize_line_item("516", "Self-Insured Claims", "expenditure") == "insurance_or_claims"
    # No account, but label still matches the fallback regex.
    assert categorize_line_item("", "General Liability Claim", "expenditure") == "insurance_or_claims"


def test_benefits_accounts() -> None:
    assert categorize_line_item("207", "Medical Insurance", "expenditure") == "benefits_or_payroll_burden"
    assert categorize_line_item("212", "BONUS Medicare Liability", "expenditure") == "benefits_or_payroll_burden"
    assert categorize_line_item("201", "Social Security", "expenditure") == "benefits_or_payroll_burden"


def test_personnel_account_range_excludes_benefits() -> None:
    assert categorize_line_item("105", "Supervisor/Director", "expenditure") == "personnel"
    assert categorize_line_item("161", "Secretary", "expenditure") == "personnel"
    # 201 is outside the 105-199 personnel range and inside the benefits set.
    assert categorize_line_item("201", "Social Security", "expenditure") != "personnel"


def test_debt_service_account_range() -> None:
    assert categorize_line_item("602", "JAIL Principal on Notes", "expenditure") == "debt_service"
    assert categorize_line_item("613", "USDA Interest on Other Loans Payable", "expenditure") == "debt_service"
    assert categorize_line_item("699", "Other Debt Service", "expenditure") == "debt_service"


def test_grant_or_intergovernmental_revenue_requires_revenue_side() -> None:
    assert (
        categorize_line_item("46980", "Other State Grants - Connected Communities Facilities", "revenue")
        == "grant_or_intergovernmental_revenue"
    )
    assert categorize_line_item("46420", "State Aid Program", "revenue") == "grant_or_intergovernmental_revenue"
    # Same account range on the expenditure side should not match -- the
    # 46xxx-47xxx range is a revenue-side convention.
    assert categorize_line_item("46980", "Other State Grants", "expenditure") != "grant_or_intergovernmental_revenue"


def test_capital_project_account_range() -> None:
    assert categorize_line_item("707", "Building Improvements", "expenditure") == "capital_project"
    assert categorize_line_item("707", "CRD Building Improvements", "expenditure") == "capital_project"
    assert categorize_line_item("706", "Building Construction", "expenditure") == "capital_project"
    assert categorize_line_item("726", "State Aid Projects", "expenditure") == "capital_project"


def test_allocation_or_recipient_payment_by_account_and_label() -> None:
    # Account 316 is Fund 101's outside-agency/contribution account.
    assert categorize_line_item("316", "OPID City of Dresden", "expenditure") == "allocation_or_recipient_payment"
    assert (
        categorize_line_item("316", "Dolly Parton Reading Railroad", "expenditure")
        == "allocation_or_recipient_payment"
    )
    # Label-based fallback for a recipient-shaped label outside account 316.
    assert (
        categorize_line_item("399", "City of Martin Housing Authority", "expenditure")
        == "allocation_or_recipient_payment"
    )


def test_contracted_services_subcategories_by_label() -> None:
    assert categorize_line_item("355", "Travel", "expenditure") == "travel"
    assert categorize_line_item("307", "Communication", "expenditure") == "communication"
    assert categorize_line_item("335", "Maintenance/Repair - Buildings", "expenditure") == "maintenance_services"
    assert categorize_line_item("399", "Other Contracted Services", "expenditure") == "contracted_services"


def test_supplies_and_materials_account_range() -> None:
    assert categorize_line_item("435", "Office Supplies", "expenditure") == "supplies_and_materials"


def test_unrecognized_account_and_label_falls_back_to_needs_human_review() -> None:
    assert categorize_line_item("99999", "Something Unusual", "expenditure") == "needs_human_review"
