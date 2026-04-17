"""Tests for survey_system.exceptions."""

from __future__ import annotations

from survey_system.exceptions import (
    ConfigurationError,
    LLMError,
    SurveySchemaError,
    SurveySystemError,
    ValidationError,
    wrap_exception,
)


def test_survey_system_error_message() -> None:
    """``SurveySystemError`` stores message and stringifies without details."""
    err = SurveySystemError("oops")
    assert err.message == "oops"
    assert str(err) == "oops"
    assert err.details is None


def test_survey_system_error_with_details() -> None:
    """``SurveySystemError`` includes details in ``str`` when provided."""
    err = SurveySystemError("bad", details={"field": "age", "code": 1})
    assert "bad" in str(err)
    assert "field" in str(err)


def test_subclass_inheritance() -> None:
    """Domain errors inherit from ``SurveySystemError``."""
    assert issubclass(ConfigurationError, SurveySystemError)
    assert issubclass(ValidationError, SurveySystemError)
    assert issubclass(LLMError, SurveySystemError)
    assert issubclass(SurveySchemaError, SurveySystemError)


def test_wrap_exception_sets_cause() -> None:
    """``wrap_exception`` chains the original exception as ``__cause__``."""
    try:
        raise ValueError("inner")
    except ValueError as exc:
        wrapped = wrap_exception(
            exc,
            message="outer",
            error_class=LLMError,
            details={"step": "call"},
        )
    assert isinstance(wrapped, LLMError)
    assert wrapped.__cause__ is not None
    assert isinstance(wrapped.__cause__, ValueError)

