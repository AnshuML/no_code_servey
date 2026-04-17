"""Tests for SurveyAIEngine parse shortcuts."""

from __future__ import annotations

from unittest.mock import MagicMock

from survey_system.ai.engine import SurveyAIEngine
from survey_system.schema.survey import Question, QuestionType


def test_parse_free_text_uses_raw_string() -> None:
    """Free-text answers skip the LLM and return stripped text."""
    q = Question(
        id="x",
        text="Details",
        type=QuestionType.FREE_TEXT,
    )
    eng = SurveyAIEngine(MagicMock())
    out = eng.parse_answer(q, "  Rohan ladka school  ")
    assert out["value"] == "Rohan ladka school"


def test_parse_number_extracts_digits() -> None:
    """Numeric answers extract the first number from messy input."""
    q = Question(
        id="n",
        text="Income",
        type=QuestionType.NUMBER,
    )
    eng = SurveyAIEngine(MagicMock())
    out = eng.parse_answer(q, "lagbhag 65000 rupaye")
    assert out["value"] == 65000


def test_validate_answer_skips_groq_when_rules_pass() -> None:
    """Second Groq validation call is not used when schema rules already pass."""
    q = Question(
        id="x",
        text="Details",
        type=QuestionType.FREE_TEXT,
    )
    client = MagicMock()
    eng = SurveyAIEngine(client)
    out = eng.validate_answer(q, {"value": "typed answer", "confidence": 1.0})
    assert out["valid"] is True
    client.chat_completion_json.assert_not_called()


def test_validate_answer_falls_back_when_rules_fail_and_groq_errors() -> None:
    """If rules fail and Groq errors, still return a safe invalid payload."""
    q = Question(
        id="x",
        text="Pick",
        type=QuestionType.SINGLE_CHOICE,
        options=["A", "B"],
    )
    client = MagicMock()
    from survey_system.exceptions import LLMError

    client.chat_completion_json.side_effect = LLMError("down", details={})
    eng = SurveyAIEngine(client)
    out = eng.validate_answer(q, {"value": "Z"})
    assert out["valid"] is False
    assert out["issues"]
