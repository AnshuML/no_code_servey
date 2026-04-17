"""Pydantic models for JSON-based survey definitions."""

from __future__ import annotations

import json
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator

from survey_system.exceptions import SurveySchemaError

# After this question, end the survey (no more questions).
END_SURVEY_NAV = "__END__"


class QuestionType(str, Enum):
    """Supported question input kinds."""

    FREE_TEXT = "free_text"
    SINGLE_CHOICE = "single_choice"
    NUMBER = "number"
    YES_NO = "yes_no"


class Question(BaseModel):
    """A single survey question."""

    id: str = Field(..., min_length=1)
    text: str = Field(..., min_length=1)
    type: QuestionType
    options: list[str] | None = None
    required: bool = True
    min_value: float | None = None
    max_value: float | None = None
    next_question_id: str | None = Field(
        default=None,
        description=(
            "If set: after a valid answer, go to this question id, or use "
            f"'{END_SURVEY_NAV}' to finish. If null: use the next question in survey order."
        ),
    )

    @field_validator("options", mode="before")
    @classmethod
    def strip_option_whitespace(cls, value: Any) -> Any:
        """Normalize option strings when a list is provided.

        Args:
            value: Raw options value.

        Returns:
            Stripped strings or unchanged value.
        """
        if value is None:
            return None
        if not isinstance(value, list):
            raise SurveySchemaError(
                "options must be a list of strings or null",
                details={"field": "options"},
            )
        out: list[str] = []
        for item in value:
            if not isinstance(item, str):
                raise SurveySchemaError(
                    "each option must be a string",
                    details={"field": "options"},
                )
            s = item.strip()
            if s:
                out.append(s)
        return out or None

    @model_validator(mode="after")
    def check_options_for_choice(self) -> Question:
        """Ensure choice-style questions define options.

        Returns:
            Validated question.

        Raises:
            SurveySchemaError: When options are missing for choice types.
        """
        if self.type == QuestionType.SINGLE_CHOICE and not self.options:
            raise SurveySchemaError(
                "single_choice questions require non-empty options",
                details={"question_id": self.id},
            )
        if self.type in (QuestionType.YES_NO, QuestionType.NUMBER, QuestionType.FREE_TEXT):
            if self.options:
                raise SurveySchemaError(
                    f"options are not used for question type {self.type.value}",
                    details={"question_id": self.id},
                )
        return self


class Survey(BaseModel):
    """A versioned survey definition."""

    schema_version: str = Field(default="1.0")
    id: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1)
    questions: list[Question] = Field(default_factory=list)

    @field_validator("questions")
    @classmethod
    def unique_question_ids(cls, questions: list[Question]) -> list[Question]:
        """Ensure question IDs are unique within the survey.

        Args:
            questions: Parsed questions.

        Returns:
            Same list when valid.

        Raises:
            SurveySchemaError: When duplicate IDs exist.
        """
        seen: set[str] = set()
        for q in questions:
            if q.id in seen:
                raise SurveySchemaError(
                    "duplicate question id",
                    details={"question_id": q.id},
                )
            seen.add(q.id)
        return questions

    @model_validator(mode="after")
    def check_next_question_ids(self) -> Survey:
        """Ensure ``next_question_id`` references exist when set."""
        ids = {q.id for q in self.questions}
        for q in self.questions:
            nxt = q.next_question_id
            if nxt is None or nxt == END_SURVEY_NAV:
                continue
            if nxt not in ids:
                raise SurveySchemaError(
                    "next_question_id must be null, "
                    f"{END_SURVEY_NAV!r}, or an existing question id",
                    details={"question_id": q.id, "next_question_id": nxt},
                )
        return self


def survey_from_json_bytes(data: bytes) -> Survey:
    """Parse a UTF-8 JSON byte string into a :class:`Survey`.

    Args:
        data: Raw JSON bytes.

    Returns:
        Validated survey model.

    Raises:
        SurveySchemaError: On invalid JSON or schema.
    """
    try:
        text = data.decode("utf-8")
        payload = json.loads(text)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SurveySchemaError(
            "survey JSON could not be parsed",
            details={"error": type(exc).__name__},
        ) from exc
    return survey_from_dict(payload)


def survey_from_dict(payload: dict[str, Any]) -> Survey:
    """Validate a mapping as a :class:`Survey`.

    Args:
        payload: Parsed JSON object.

    Returns:
        Validated survey model.

    Raises:
        SurveySchemaError: On validation failure.
    """
    try:
        return Survey.model_validate(payload)
    except SurveySchemaError:
        raise
    except ValidationError as exc:
        raise SurveySchemaError(
            "invalid survey schema",
            details={"validation_errors": exc.errors()},
        ) from exc
    except Exception as exc:
        raise SurveySchemaError(
            "invalid survey schema",
            details={"error": type(exc).__name__},
        ) from exc
