"""Tests for survey_system.config."""

from __future__ import annotations

import pytest

from survey_system.config import Environment, Settings, get_settings, reset_settings_cache
from survey_system.exceptions import ConfigurationError


@pytest.fixture(autouse=True)
def _clear_settings_cache() -> None:
    """Ensure each test sees fresh settings."""
    reset_settings_cache()
    yield
    reset_settings_cache()


def test_settings_dev_allows_empty_groq(monkeypatch: pytest.MonkeyPatch) -> None:
    """Development mode does not require ``GROQ_API_KEY``."""
    monkeypatch.setenv("GROQ_API_KEY", "")
    monkeypatch.setenv("SURVEY_ENVIRONMENT", "dev")
    s = Settings(_env_file=None)
    assert s.environment == Environment.DEV
    assert s.groq_api_key == ""


def test_settings_prod_requires_groq(monkeypatch: pytest.MonkeyPatch) -> None:
    """Production mode raises when ``GROQ_API_KEY`` is missing."""
    monkeypatch.setenv("GROQ_API_KEY", "")
    monkeypatch.setenv("SURVEY_ENVIRONMENT", "prod")
    with pytest.raises(ConfigurationError) as exc_info:
        Settings(_env_file=None)
    assert "GROQ_API_KEY" in str(exc_info.value)


def test_log_level_validation(monkeypatch: pytest.MonkeyPatch) -> None:
    """Empty ``LOG_LEVEL`` raises ``ConfigurationError``."""
    monkeypatch.setenv("LOG_LEVEL", "")
    monkeypatch.setenv("SURVEY_ENVIRONMENT", "dev")
    with pytest.raises(ConfigurationError):
        Settings(_env_file=None)


def test_get_settings_cached(monkeypatch: pytest.MonkeyPatch) -> None:
    """``get_settings`` returns a cached instance."""
    monkeypatch.setenv("SURVEY_ENVIRONMENT", "dev")
    monkeypatch.setenv("GROQ_API_KEY", "")
    a = get_settings()
    b = get_settings()
    assert a is b
