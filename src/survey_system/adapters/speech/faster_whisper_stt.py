"""Local open-source STT via `faster-whisper` (MIT). Install: ``pip install -e ".[voice]"``."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from survey_system.exceptions import SurveySystemError


class FasterWhisperSpeechToText:
    """Speech-to-text using CTranslate2 + Whisper weights (no cloud STT)."""

    def __init__(
        self,
        model_size: str = "tiny",
        device: str = "cpu",
        compute_type: str = "int8",
        *,
        _model: Any | None = None,
    ) -> None:
        """Load Whisper. Pass ``_model`` only in tests.

        Args:
            model_size: Whisper size name (``tiny``, ``base``, …).
            device: ``cpu`` or ``cuda``.
            compute_type: e.g. ``int8`` (CPU) or ``float16`` (GPU).
            _model: Injected fake model for unit tests.
        """
        if _model is not None:
            self._model = _model
            return
        try:
            from faster_whisper import WhisperModel
        except ImportError as exc:
            raise ImportError(
                "faster-whisper is not installed. Run: pip install -e \".[voice]\""
            ) from exc
        self._model = WhisperModel(
            model_size,
            device=device,
            compute_type=compute_type,
        )

    def transcribe(self, audio: bytes, *, language_hint: str | None = None) -> str:
        """Transcribe WAV (or other ffmpeg-supported) bytes to UTF-8 text."""
        if not audio:
            raise SurveySystemError("Empty audio payload", details={})
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(audio)
            path = tmp.name
        try:
            segments, _info = self._model.transcribe(
                path,
                language=(language_hint.strip() or None) if language_hint else None,
                vad_filter=True,
            )
            parts = [s.text.strip() for s in segments if s.text.strip()]
            return " ".join(parts).strip()
        finally:
            Path(path).unlink(missing_ok=True)
