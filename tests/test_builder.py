"""Tests for survey builder helpers."""

from __future__ import annotations

from unittest.mock import MagicMock

from survey_system.exceptions import SurveySchemaError
from survey_system.survey_builder.builder import build_survey_from_prompt, load_survey_from_json_text


def test_load_survey_from_json_text() -> None:
    """JSON text loads into a survey model."""
    text = '{"id":"x","title":"t","questions":[]}'
    s = load_survey_from_json_text(text)
    assert s.id == "x"


def test_build_survey_from_prompt_validates() -> None:
    """Prompt builder wraps invalid LLM output as ``SurveySchemaError``."""
    client = MagicMock()
    client.chat_completion_json.return_value = {"not": "a survey"}
    try:
        build_survey_from_prompt(client, "make a survey")
    except SurveySchemaError:
        return
    raise AssertionError("expected SurveySchemaError")
