"""Placeholder STT until a real open-source backend is wired (Whisper, Vosk, …)."""

from __future__ import annotations

from survey_system.exceptions import SurveySystemError


class UnavailableSpeechToText:
    """Raises if voice is requested before an OSS STT adapter is configured."""

    def transcribe(self, audio: bytes, *, language_hint: str | None = None) -> str:
        raise SurveySystemError(
            "Speech-to-text is not configured. "
            "Implement SpeechToText with e.g. faster-whisper or Vosk (open source).",
            details={"audio_len": len(audio), "language_hint": language_hint},
        )
