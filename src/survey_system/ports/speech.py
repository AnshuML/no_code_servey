"""Speech port: plug in Whisper/Vosk/etc. without touching the survey engine."""

from __future__ import annotations

from typing import Protocol


class SpeechToText(Protocol):
    """Convert audio bytes to transcript text (open-source backends: Whisper, Vosk, …)."""

    def transcribe(self, audio: bytes, *, language_hint: str | None = None) -> str:
        """Return UTF-8 text from raw audio (format defined by implementation)."""
        ...
