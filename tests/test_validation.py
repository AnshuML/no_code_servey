"""Tests for rule-based validation."""

from __future__ import annotations

from survey_system.schema.survey import Question, QuestionType
from survey_system.validation.pipeline import validate_rules


def test_single_choice_valid() -> None:
    """Valid choice passes."""
    q = Question(
        id="q1",
        text="Pick",
        type=QuestionType.SINGLE_CHOICE,
        options=["A", "B"],
    )
    r = validate_rules(q, "A")
    assert r.valid is True


def test_single_choice_invalid_option() -> None:
    """Unknown option fails."""
    q = Question(
        id="q1",
        text="Pick",
        type=QuestionType.SINGLE_CHOICE,
        options=["A", "B"],
    )
    r = validate_rules(q, "C")
    assert r.valid is False


def test_number_bounds() -> None:
    """Numeric bounds are enforced."""
    q = Question(
        id="q1",
        text="Age",
        type=QuestionType.NUMBER,
        min_value=0,
        max_value=10,
    )
    assert validate_rules(q, 5).valid is True
    assert validate_rules(q, 11).valid is False
