"""Environment-based application settings."""

from __future__ import annotations

import logging
from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import AliasChoices, Field, ValidationError, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from survey_system.exceptions import ConfigurationError

logger = logging.getLogger(__name__)


class Environment(str, Enum):
    """Deployment environment."""

    DEV = "dev"
    PROD = "prod"


class Settings(BaseSettings):
    """Load configuration from environment variables and optional ``.env`` file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
        populate_by_name=True,
    )

    environment: Environment = Field(
        default=Environment.DEV,
        description="dev allows missing API keys; prod requires them.",
        validation_alias=AliasChoices("SURVEY_ENVIRONMENT", "ENVIRONMENT"),
    )
    groq_api_key: str = Field(default="", description="Groq API key")
    groq_model: str = Field(default="llama-3.3-70b-versatile")
    https_proxy: str = Field(
        default="",
        description="Optional proxy for Groq HTTPS (office networks). "
        "Also set env HTTPS_PROXY / HTTP_PROXY; httpx uses trust_env.",
        validation_alias=AliasChoices("HTTPS_PROXY", "HTTP_PROXY"),
    )
    huggingface_token: str = Field(default="", description="Optional HF token")
    embedding_model_name: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2",
    )
    faiss_index_path: Path | None = Field(
        default=None,
        description="Optional path to persist FAISS index",
    )
    log_level: str = Field(default="INFO")
    log_json: bool = Field(default=False)

    # Local open-source STT (faster-whisper). Optional; see ``[voice]`` extra in pyproject.toml.
    whisper_model_size: str = Field(
        default="tiny",
        description="Whisper model id for faster-whisper (tiny/base/small/…).",
        validation_alias=AliasChoices("SURVEY_WHISPER_MODEL", "WHISPER_MODEL"),
    )
    whisper_device: str = Field(
        default="cpu",
        description="cpu or cuda",
        validation_alias=AliasChoices("SURVEY_WHISPER_DEVICE", "WHISPER_DEVICE"),
    )
    whisper_compute_type: str = Field(
        default="int8",
        description="e.g. int8 on CPU, float16 on GPU",
        validation_alias=AliasChoices("SURVEY_WHISPER_COMPUTE_TYPE", "WHISPER_COMPUTE_TYPE"),
    )
    whisper_language: str = Field(
        default="",
        description="ISO 639-1 hint (hi, en); empty = auto-detect",
        validation_alias=AliasChoices("SURVEY_WHISPER_LANGUAGE", "WHISPER_LANGUAGE"),
    )

    # WhatsApp Cloud API (optional channel). See docs/WHATSAPP_SETUP.md
    whatsapp_verify_token: str = Field(
        default="",
        description="Webhook verify token (Meta dashboard).",
        validation_alias="WHATSAPP_VERIFY_TOKEN",
    )
    whatsapp_access_token: str = Field(
        default="",
        description="Graph API permanent or system user token for sending.",
        validation_alias=AliasChoices("WHATSAPP_ACCESS_TOKEN", "WHATSAPP_TOKEN"),
    )
    whatsapp_phone_number_id: str = Field(
        default="",
        description="WhatsApp phone_number_id from Meta.",
        validation_alias="WHATSAPP_PHONE_NUMBER_ID",
    )
    whatsapp_app_secret: str = Field(
        default="",
        description="Optional App Secret for X-Hub-Signature-256 verification.",
        validation_alias="WHATSAPP_APP_SECRET",
    )
    whatsapp_graph_api_version: str = Field(
        default="v21.0",
        validation_alias="WHATSAPP_GRAPH_VERSION",
    )
    whatsapp_survey_json_path: str = Field(
        default="",
        description="Optional UTF-8 JSON file path; default = bundled family survey.",
        validation_alias="WHATSAPP_SURVEY_JSON",
    )

    @field_validator("log_level", mode="before")
    @classmethod
    def normalize_log_level(cls, value: Any) -> str:
        """Return a non-empty uppercase log level string.

        Args:
            value: Raw env value.

        Returns:
            Normalized log level name.

        Raises:
            ConfigurationError: If the value is empty or not a string.
        """
        if value is None or (isinstance(value, str) and not value.strip()):
            raise ConfigurationError(
                "LOG_LEVEL must be a non-empty string",
                details={"field": "log_level"},
            )
        if not isinstance(value, str):
            raise ConfigurationError(
                "LOG_LEVEL must be a string",
                details={"field": "log_level", "got": type(value).__name__},
            )
        return value.strip().upper()

    @field_validator(
        "groq_api_key",
        "huggingface_token",
        "whatsapp_verify_token",
        "whatsapp_access_token",
        "whatsapp_phone_number_id",
        "whatsapp_app_secret",
        mode="before",
    )
    @classmethod
    def strip_secrets(cls, value: Any) -> str:
        """Strip whitespace from secret fields; coerce ``None`` to empty string.

        Args:
            value: Raw secret value.

        Returns:
            Stripped string or empty string.
        """
        if value is None:
            return ""
        if not isinstance(value, str):
            raise ConfigurationError(
                "API token fields must be strings",
                details={"field": "secrets", "got": type(value).__name__},
            )
        return value.strip()

    @field_validator("whatsapp_graph_api_version", mode="before")
    @classmethod
    def whatsapp_graph_version_or_default(cls, value: Any) -> str:
        if value is None or (isinstance(value, str) and not value.strip()):
            return "v21.0"
        if not isinstance(value, str):
            raise ConfigurationError(
                "WHATSAPP_GRAPH_VERSION must be a string",
                details={"got": type(value).__name__},
            )
        return value.strip()

    @field_validator("whatsapp_survey_json_path", mode="before")
    @classmethod
    def strip_whatsapp_survey_path(cls, value: Any) -> str:
        if value is None:
            return ""
        if not isinstance(value, str):
            raise ConfigurationError(
                "WHATSAPP_SURVEY_JSON must be a string",
                details={"got": type(value).__name__},
            )
        return value.strip()

    @field_validator("whisper_model_size", mode="before")
    @classmethod
    def whisper_model_size_or_default(cls, value: Any) -> str:
        """Non-empty model name; default ``tiny``."""
        if value is None or (isinstance(value, str) and not value.strip()):
            return "tiny"
        if not isinstance(value, str):
            raise ConfigurationError(
                "SURVEY_WHISPER_MODEL must be a string",
                details={"got": type(value).__name__},
            )
        return value.strip()

    @field_validator("whisper_compute_type", mode="before")
    @classmethod
    def whisper_compute_type_or_default(cls, value: Any) -> str:
        """Non-empty compute type; default ``int8``."""
        if value is None or (isinstance(value, str) and not value.strip()):
            return "int8"
        if not isinstance(value, str):
            raise ConfigurationError(
                "SURVEY_WHISPER_COMPUTE_TYPE must be a string",
                details={"got": type(value).__name__},
            )
        return value.strip()

    @field_validator("whisper_language", mode="before")
    @classmethod
    def strip_whisper_language(cls, value: Any) -> str:
        """Optional BCP-47 / ISO-639-1 hint; empty = auto-detect in STT."""
        if value is None:
            return ""
        if not isinstance(value, str):
            raise ConfigurationError(
                "SURVEY_WHISPER_LANGUAGE must be a string",
                details={"got": type(value).__name__},
            )
        return value.strip()

    @field_validator("whisper_device", mode="before")
    @classmethod
    def normalize_whisper_device(cls, value: Any) -> str:
        """Allow only cpu or cuda for faster-whisper device."""
        if value is None:
            return "cpu"
        if not isinstance(value, str):
            raise ConfigurationError(
                "SURVEY_WHISPER_DEVICE must be a string",
                details={"got": type(value).__name__},
            )
        v = value.strip().lower()
        if v not in ("cpu", "cuda"):
            raise ConfigurationError(
                "SURVEY_WHISPER_DEVICE must be 'cpu' or 'cuda'",
                details={"value": value},
            )
        return v

    @field_validator("https_proxy", mode="before")
    @classmethod
    def strip_proxy(cls, value: Any) -> str:
        """Normalize optional HTTP(S) proxy URL."""
        if value is None:
            return ""
        if not isinstance(value, str):
            raise ConfigurationError(
                "HTTPS_PROXY must be a string",
                details={"field": "https_proxy"},
            )
        return value.strip()

    @model_validator(mode="after")
    def require_keys_in_prod(self) -> Settings:
        """Ensure required secrets exist when ``environment`` is production.

        Returns:
            Validated settings instance.

        Raises:
            ConfigurationError: If production is missing ``groq_api_key``.
        """
        if self.environment == Environment.PROD and not self.groq_api_key:
            logger.error(
                "configuration_invalid",
                extra={"reason": "missing_groq_api_key", "environment": "prod"},
            )
            raise ConfigurationError(
                "GROQ_API_KEY is required when SURVEY_ENVIRONMENT=prod",
                details={"environment": "prod"},
            )
        if self.environment == Environment.DEV and not self.groq_api_key:
            logger.warning(
                "configuration_dev_missing_groq_key",
                extra={"hint": "LLM features will fail until GROQ_API_KEY is set"},
            )
        return self


def _safe_settings_summary(settings: Settings) -> dict[str, Any]:
    """Build a debug-safe summary of settings (no secret values).

    Args:
        settings: Loaded settings.

    Returns:
        Dict suitable for structured logging.
    """
    return {
        "environment": settings.environment.value,
        "groq_model": settings.groq_model,
        "embedding_model_name": settings.embedding_model_name,
        "faiss_index_path": str(settings.faiss_index_path)
        if settings.faiss_index_path
        else None,
        "log_level": settings.log_level,
        "log_json": settings.log_json,
        "has_groq_api_key": bool(settings.groq_api_key),
        "has_huggingface_token": bool(settings.huggingface_token),
        "has_https_proxy": bool(settings.https_proxy),
        "whisper_model_size": settings.whisper_model_size,
        "whisper_device": settings.whisper_device,
        "whisper_compute_type": settings.whisper_compute_type,
        "whisper_language_set": bool(settings.whisper_language.strip()),
        "whatsapp_webhook_ready": bool(settings.whatsapp_verify_token.strip()),
        "whatsapp_send_ready": bool(
            settings.whatsapp_access_token.strip() and settings.whatsapp_phone_number_id.strip()
        ),
        "whatsapp_survey_json_set": bool(settings.whatsapp_survey_json_path.strip()),
    }


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Load and cache settings from the environment.

    Returns:
        Validated :class:`Settings` instance.

    Raises:
        ConfigurationError: When validation fails.
    """
    try:
        settings = Settings()
    except ConfigurationError:
        raise
    except ValidationError as exc:
        logger.warning("settings_validation_failed", extra={"errors": exc.errors()})
        raise ConfigurationError(
            "Invalid application settings",
            details={"validation_errors": exc.errors()},
        ) from exc
    except Exception as exc:
        logger.exception("settings_load_failed")
        raise ConfigurationError(
            "Failed to load application settings",
            details={"error": type(exc).__name__},
        ) from exc

    logger.info("settings_loaded", extra=_safe_settings_summary(settings))
    return settings


def reset_settings_cache() -> None:
    """Clear the cached settings (for tests)."""
    get_settings.cache_clear()
