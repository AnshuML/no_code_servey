"""Create surveys from JSON text or natural-language prompts (via Groq)."""

from __future__ import annotations

import json
from typing import Any

from survey_system.ai.groq_client import GroqClient
from survey_system.exceptions import LLMError, SurveySchemaError
from survey_system.schema.survey import Survey, survey_from_dict


def load_survey_from_json_text(text: str) -> Survey:
    """Parse a JSON string into a :class:`~survey_system.schema.survey.Survey`.

    Args:
        text: UTF-8 JSON text.

    Returns:
        Validated survey.

    Raises:
        SurveySchemaError: When JSON or schema validation fails.
    """
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise SurveySchemaError(
            "survey JSON could not be parsed",
            details={"error": type(exc).__name__},
        ) from exc
    if not isinstance(payload, dict):
        raise SurveySchemaError("survey JSON must be an object", details={})
    return survey_from_dict(payload)


def build_survey_from_prompt(client: GroqClient, prompt: str) -> Survey:
    """Use Groq to generate a survey JSON object from a short natural-language prompt.

    Args:
        client: Groq client.
        prompt: User description of the survey.

    Returns:
        Validated survey model.

    Raises:
        LLMError: When the LLM fails.
        SurveySchemaError: When the model output is not a valid survey.
    """
    system = (
        "You are a survey designer. Respond ONLY with JSON for this schema keys: "
        '{"schema_version":"1.0","id":string,"title":string,'
        '"questions":[{"id":string,"text":string,'
        '"type":"free_text"|"single_choice"|"number"|"yes_no",'
        '"options":[string] (only for single_choice),'
        '"required":boolean}]}. '
        "Use realistic ids. Keep questions concise."
    )
    user = f"Create a small survey (3-6 questions) for: {prompt}"
    try:
        data: dict[str, Any] = client.chat_completion_json(system=system, user=user)
    except LLMError:
        raise
    except Exception as exc:
        raise LLMError(
            "failed to generate survey from prompt",
            details={"error": type(exc).__name__},
        ) from exc
    try:
        return survey_from_dict(data)
    except SurveySchemaError as exc:
        raise SurveySchemaError(
            "LLM produced an invalid survey schema",
            details={"cause": str(exc)},
        ) from exc
