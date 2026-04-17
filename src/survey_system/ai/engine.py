"""High-level AI operations for survey answering and validation."""

from __future__ import annotations

import re
from typing import Any

from survey_system.ai.groq_client import GroqClient
from survey_system.exceptions import LLMError
from survey_system.schema.survey import Question, QuestionType
from survey_system.validation.pipeline import validate_rules


def _question_type_hint(question: Question) -> str:
    """Return a short string describing expected structured value shape.

    Args:
        question: Current question.

    Returns:
        Instruction fragment for the LLM.
    """
    if question.type == QuestionType.SINGLE_CHOICE:
        opts = ", ".join(question.options or [])
        return f"single_choice: value must be one of: {opts}"
    if question.type == QuestionType.YES_NO:
        return "yes_no: boolean yes/no as JSON boolean true/false"
    if question.type == QuestionType.NUMBER:
        return "number: numeric JSON number"
    return "free_text: short string"


class SurveyAIEngine:
    """Groq-backed parsing, validation, and follow-up suggestions."""

    def __init__(self, client: GroqClient) -> None:
        """Initialize with a Groq client.

        Args:
            client: Configured :class:`GroqClient`.
        """
        self._client = client

    def parse_answer(self, question: Question, user_text: str) -> dict[str, Any]:
        """Convert natural language into a structured JSON value for the question.

        Args:
            question: Active question definition.
            user_text: Raw user message.

        Returns:
            A dict with keys ``value`` and optional ``confidence`` in ``[0,1]``.

        Raises:
            LLMError: When the model fails or returns invalid JSON.
        """
        if question.type == QuestionType.FREE_TEXT:
            stripped = (user_text or "").strip()
            return {"value": stripped, "confidence": 1.0 if stripped else 0.0}

        if question.type == QuestionType.NUMBER:
            compact = (user_text or "").replace(",", "").strip()
            match = re.search(r"-?\d+(?:\.\d+)?", compact)
            if match:
                token = match.group()
                num: float | int = float(token) if "." in token else int(token)
                return {"value": num, "confidence": 0.95}

        system = (
            "You convert survey answers into strict JSON. "
            "Respond ONLY with JSON: {\"value\": ..., \"confidence\": 0-1}."
        )
        user = (
            f"Question ({question.type.value}): {question.text}\n"
            f"Constraints: {_question_type_hint(question)}\n"
            f"User answer: {user_text!r}\n"
        )
        data = self._client.chat_completion_json(system=system, user=user)
        if "value" not in data:
            raise LLMError("model JSON missing 'value' key", details={"keys": list(data)})
        return data

    def validate_answer(
        self,
        question: Question,
        structured: dict[str, Any],
    ) -> dict[str, Any]:
        """Validate using schema rules first; only call Groq when rules already fail.

        When deterministic rules pass, we skip an extra Groq round-trip (faster,
        works offline for parse/validate, and avoids failures on the second call).

        Args:
            question: Active question.
            structured: Parsed structured payload (expects ``value``).

        Returns:
            JSON with keys: ``valid`` (bool), ``issues`` (list[str]), ``suggested_fix`` (str|null).
        """
        value = structured.get("value")
        rules = validate_rules(question, value)
        if rules.valid:
            return {"valid": True, "issues": [], "suggested_fix": None}

        system = (
            "You validate survey answers. Respond ONLY with JSON: "
            '{"valid": bool, "issues": [string], "suggested_fix": string|null}.'
        )
        user = (
            f"Question ({question.type.value}): {question.text}\n"
            f"Constraints: {_question_type_hint(question)}\n"
            f"Structured: {structured!r}\n"
        )
        try:
            return self._client.chat_completion_json(system=system, user=user)
        except LLMError:
            return {"valid": False, "issues": list(rules.issues), "suggested_fix": None}

    def suggest_followup(
        self,
        question: Question,
        structured: dict[str, Any],
        validation: dict[str, Any],
    ) -> str:
        """Ask the model for a concise follow-up prompt for the user.

        Args:
            question: Active question.
            structured: Parsed structured payload.
            validation: Validation result from :meth:`validate_answer`.

        Returns:
            Short follow-up question text.
        """
        system = (
            "You write a short, polite follow-up question to clarify an invalid answer. "
            'Respond ONLY with JSON: {"follow_up": string}.'
        )
        user = (
            f"Question: {question.text}\n"
            f"Parsed: {structured!r}\n"
            f"Validation: {validation!r}\n"
        )
        data = self._client.chat_completion_json(system=system, user=user)
        follow = data.get("follow_up")
        if not isinstance(follow, str) or not follow.strip():
            raise LLMError("model JSON missing follow_up string", details={"keys": list(data)})
        return follow.strip()
