from budget_audit.questions import dedupe_questions, questions_for_category


def test_questions_for_category_matches_category() -> None:
    capital_questions = questions_for_category("capital_project")
    insurance_questions = questions_for_category("insurance_or_claims")

    assert any("bid documents" in q for q in capital_questions)
    assert not any("bid documents" in q for q in insurance_questions)
    assert any("premium assumptions" in q for q in insurance_questions)


def test_questions_for_category_falls_back_to_needs_human_review() -> None:
    assert questions_for_category("some_unknown_category") == questions_for_category("needs_human_review")


def test_dedupe_questions_preserves_first_seen_order() -> None:
    result = dedupe_questions(["a", "b", "a", "c", "b"])
    assert result == ["a", "b", "c"]
