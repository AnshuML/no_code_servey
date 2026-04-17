"""Rule-based validation before or alongside LLM validation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from survey_system.schema.survey import Question, QuestionType


@dataclass(frozen=True)
class RuleValidationResult:
    """Outcome of deterministic validation rules."""

    valid: bool
    issues: list[str]


def validate_rules(question: Question, value: Any) -> RuleValidationResult:
    """Validate a parsed ``value`` against the question type and bounds.

    Args:
        question: Question definition.
        value: Parsed value from AI or user.

    Returns:
        :class:`RuleValidationResult`.
    """
    issues: list[str] = []
    if question.type == QuestionType.SINGLE_CHOICE:
        if not isinstance(value, str):
            issues.append("expected a string choice")
        elif question.options and value not in question.options:
            issues.append("value must be one of the provided options")
    elif question.type == QuestionType.YES_NO:
        if not isinstance(value, bool):
            issues.append("expected a boolean yes/no")
    elif question.type == QuestionType.NUMBER:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            issues.append("expected a numeric value")
        else:
            num = float(value)
            if question.min_value is not None and num < float(question.min_value):
                issues.append(f"value must be >= {question.min_value}")
            if question.max_value is not None and num > float(question.max_value):
                issues.append(f"value must be <= {question.max_value}")
    elif question.type == QuestionType.FREE_TEXT:
        if not isinstance(value, str):
            issues.append("expected a text answer")
        elif not value.strip() and question.required:
            issues.append("answer cannot be empty")
    if question.required and value is None:
        issues.append("value is required")

    valid = len(issues) == 0
    return RuleValidationResult(valid=valid, issues=issues)
