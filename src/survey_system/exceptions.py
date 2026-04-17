"""Domain-specific exceptions for the survey system."""

from __future__ import annotations

from typing import Any


def _format_details(details: dict[str, Any] | None) -> str:
    """Return a short string representation of optional error details.

    Args:
        details: Optional mapping of debug-safe key/value pairs.

    Returns:
        Empty string if ``details`` is empty or ``None``; otherwise ``" | details=..."``.
    """
    if not details:
        return ""
    safe_items = {k: v for k, v in details.items() if k != "password"}
    return f" | details={safe_items!r}"


class SurveySystemError(Exception):
    """Base error for survey system failures.

    Attributes:
        message: Human-readable description (safe for logs; no secrets).
        details: Optional structured context for debugging or APIs.
    """

    def __init__(
        self,
        message: str,
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initialize a survey system error.

        Args:
            message: Human-readable description.
            details: Optional structured context (must not contain secrets).
        """
        super().__init__(message)
        self.message: str = message
        self.details: dict[str, Any] | None = details if details else None

    def __str__(self) -> str:
        """Return a string including optional details when present."""
        base = self.message
        return f"{base}{_format_details(self.details)}"


class ConfigurationError(SurveySystemError):
    """Raised when application settings are missing or invalid."""


class ValidationError(SurveySystemError):
    """Raised when a user or model response fails validation rules."""


class LLMError(SurveySystemError):
    """Raised when the LLM provider or client fails."""


class SurveySchemaError(SurveySystemError):
    """Raised when survey JSON schema is invalid or malformed."""


class EmbeddingError(SurveySystemError):
    """Raised when embedding or vector retrieval fails."""


class SurveySessionError(SurveySystemError):
    """Raised when chat/session state is invalid or inconsistent."""


def wrap_exception(
    exc: BaseException,
    *,
    message: str,
    error_class: type[SurveySystemError] = SurveySystemError,
    details: dict[str, Any] | None = None,
) -> SurveySystemError:
    """Wrap a lower-level exception in a :class:`SurveySystemError` subclass.

    Args:
        exc: The original exception.
        message: Human-readable message for the new error.
        error_class: Survey system error type to instantiate.
        details: Optional extra context.

    Returns:
        A new exception instance with ``__cause__`` set to ``exc``.
    """
    merged = dict(details or {})
    merged.setdefault("original_type", type(exc).__name__)
    err = error_class(message, details=merged)
    err.__cause__ = exc
    return err
