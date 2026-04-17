"""Tests for faster-whisper STT adapter (no real model download)."""

from __future__ import annotations

from pathlib import Path

import pytest

from survey_system.adapters.speech.faster_whisper_stt import FasterWhisperSpeechToText


class _FakeSegment:
    def __init__(self, text: str) -> None:
        self.text = text


class _FakeModel:
    def __init__(self) -> None:
        self.paths: list[str] = []

    def transcribe(self, path: str, **kwargs: object) -> tuple[list[_FakeSegment], None]:
        self.paths.append(path)
        assert Path(path).exists()
        return [_FakeSegment("  hello  "), _FakeSegment("world")], None


def test_transcribe_writes_temp_wav_and_joins_segments() -> None:
    """``transcribe`` delegates to the underlying model and strips text."""
    fake = _FakeModel()
    stt = FasterWhisperSpeechToText(_model=fake)
    out = stt.transcribe(b"RIFFfakeWAV", language_hint="en")
    assert out == "hello world"
    assert len(fake.paths) == 1
    assert not Path(fake.paths[0]).exists()


def test_transcribe_rejects_empty_bytes() -> None:
    """Empty payload raises."""
    from survey_system.exceptions import SurveySystemError

    stt = FasterWhisperSpeechToText(_model=_FakeModel())
    with pytest.raises(SurveySystemError):
        stt.transcribe(b"")
