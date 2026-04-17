"""In-memory completed-response store (POC); swap for SQL in production."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass
class CompletedSurveyRecord:
    """One finished survey session."""

    survey_id: str
    session_id: str
    answers: dict[str, Any]
    transcript: list[dict[str, Any]]
    completed_at_utc: str


class InMemoryResponseStore:
    """Append-only store for demos; thread-safe variants belong in production adapters."""

    def __init__(self) -> None:
        self._records: list[CompletedSurveyRecord] = []

    @property
    def records(self) -> tuple[CompletedSurveyRecord, ...]:
        """Read-only view for debugging / admin UI."""
        return tuple(self._records)

    def save_completed(
        self,
        *,
        survey_id: str,
        session_id: str,
        answers: dict[str, Any],
        transcript: list[dict[str, Any]],
    ) -> None:
        ts = datetime.now(UTC).isoformat()
        self._records.append(
            CompletedSurveyRecord(
                survey_id=survey_id,
                session_id=session_id,
                answers=dict(answers),
                transcript=list(transcript),
                completed_at_utc=ts,
            )
        )
