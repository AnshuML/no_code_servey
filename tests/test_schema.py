"""Tests for survey schema models."""

from __future__ import annotations

import pytest

from survey_system.exceptions import SurveySchemaError
from survey_system.schema.survey import (
    END_SURVEY_NAV,
    QuestionType,
    Survey,
    survey_from_dict,
    survey_from_json_bytes,
)


def test_survey_roundtrip_dict() -> None:
    """Valid survey dict validates and preserves key fields."""
    data = {
        "schema_version": "1.0",
        "id": "s1",
        "title": "Test",
        "questions": [
            {
                "id": "q1",
                "text": "Pick one",
                "type": "single_choice",
                "options": ["A", "B"],
            }
        ],
    }
    s = survey_from_dict(data)
    assert s.id == "s1"
    assert s.questions[0].type == QuestionType.SINGLE_CHOICE


def test_duplicate_question_ids_rejected() -> None:
    """Duplicate question IDs raise ``SurveySchemaError``."""
    data = {
        "id": "s1",
        "title": "T",
        "questions": [
            {"id": "q1", "text": "a", "type": "free_text"},
            {"id": "q1", "text": "b", "type": "free_text"},
        ],
    }
    with pytest.raises(SurveySchemaError):
        survey_from_dict(data)


def test_survey_from_json_bytes_invalid() -> None:
    """Invalid JSON bytes raise ``SurveySchemaError``."""
    with pytest.raises(SurveySchemaError):
        survey_from_json_bytes(b"not json")


def test_next_question_id_must_reference_existing_id() -> None:
    """Invalid ``next_question_id`` raises ``SurveySchemaError``."""
    data = {
        "id": "s1",
        "title": "T",
        "questions": [
            {"id": "q1", "text": "a", "type": "free_text", "next_question_id": "missing"},
        ],
    }
    with pytest.raises(SurveySchemaError):
        survey_from_dict(data)


def test_next_question_id_end_sentinel_allowed() -> None:
    """``END_SURVEY_NAV`` is a valid next target."""
    data = {
        "id": "s1",
        "title": "T",
        "questions": [
            {"id": "q1", "text": "a", "type": "free_text", "next_question_id": END_SURVEY_NAV},
        ],
    }
    s = survey_from_dict(data)
    assert s.questions[0].next_question_id == END_SURVEY_NAV
