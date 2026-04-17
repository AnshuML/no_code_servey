"""Tests for survey_system.logger."""

from __future__ import annotations

import json

import pytest

from survey_system.config import Environment, Settings, reset_settings_cache
from survey_system.logger import (
    configure_logging,
    get_logger,
    reset_logging_configuration,
)


@pytest.fixture(autouse=True)
def _reset_logging_and_settings() -> None:
    """Isolate logging configuration between tests."""
    reset_logging_configuration()
    reset_settings_cache()
    yield
    reset_logging_configuration()
    reset_settings_cache()


def _minimal_settings(**overrides: object) -> Settings:
    """Build settings without reading ``.env`` (explicit fields only)."""
    base: dict[str, object] = {
        "environment": Environment.DEV,
        "groq_api_key": "",
        "groq_model": "test-model",
        "huggingface_token": "",
        "embedding_model_name": "sentence-transformers/all-MiniLM-L6-v2",
        "faiss_index_path": None,
        "log_level": "INFO",
        "log_json": False,
    }
    base.update(overrides)
    return Settings.model_validate(base)


def test_configure_logging_idempotent() -> None:
    """Calling ``configure_logging`` twice does not add duplicate handlers."""
    settings = _minimal_settings()
    configure_logging(settings)
    root = __import__("logging").getLogger()
    n1 = len(root.handlers)
    configure_logging(settings)
    n2 = len(root.handlers)
    assert n1 == n2


def test_get_logger_emits_json_when_configured(capsys: pytest.CaptureFixture[str]) -> None:
    """JSON mode emits parseable JSON on stdout."""
    settings = _minimal_settings(log_json=True)
    configure_logging(settings)
    log = get_logger("test_json")
    log.info("hello_event", answer_id=1)
    captured = capsys.readouterr()
    line = captured.out.strip().splitlines()[-1]
    payload = json.loads(line)
    assert payload.get("event") == "hello_event" or "hello_event" in str(payload)


def test_parse_log_level_invalid() -> None:
    """Invalid log level strings raise ``ValueError`` from configuration."""
    from survey_system.logger import _parse_log_level

    with pytest.raises(ValueError):
        _parse_log_level("NOT_A_LEVEL")
