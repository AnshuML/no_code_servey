"""Persistence port: completed responses (swap in-memory → DB in production)."""

from __future__ import annotations

from typing import Any, Protocol


class ResponsePersistence(Protocol):
    """Store a finished survey session (answers + transcript).

    Implementations: :class:`~survey_system.adapters.persistence.memory.InMemoryResponseStore`
    for POC; replace with PostgreSQL/SQLite adapter for production.
    """

    def save_completed(
        self,
        *,
        survey_id: str,
        session_id: str,
        answers: dict[str, Any],
        transcript: list[dict[str, Any]],
    ) -> None:
        """Persist one completed run."""
        ...
