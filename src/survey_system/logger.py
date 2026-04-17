"""Structured logging setup and logger factory."""

from __future__ import annotations

import logging
import sys

import structlog
from structlog.stdlib import BoundLogger

from survey_system.config import Settings

_CONFIGURED = False


def _parse_log_level(level_name: str) -> int:
    """Convert a log level name to a ``logging`` numeric level.

    Args:
        level_name: Uppercase level name (e.g. ``INFO``).

    Returns:
        Numeric level constant.

    Raises:
        ValueError: If the level name is unknown.
    """
    parsed = logging.getLevelName(level_name)
    if isinstance(parsed, int):
        return parsed
    raise ValueError(f"Unknown log level: {level_name!r}")


def configure_logging(settings: Settings) -> None:
    """Configure structlog and the stdlib root logger once (idempotent).

    Args:
        settings: Application settings controlling level and JSON vs console output.
    """
    global _CONFIGURED
    if _CONFIGURED:
        return

    level = _parse_log_level(settings.log_level)
    timestamper = structlog.processors.TimeStamper(fmt="iso", utc=True)

    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        timestamper,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if settings.log_json:
        structlog.configure(
            processors=[
                *shared_processors,
                structlog.processors.JSONRenderer(),
            ],
            wrapper_class=structlog.stdlib.BoundLogger,
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True,
        )
    else:
        structlog.configure(
            processors=[
                *shared_processors,
                structlog.dev.ConsoleRenderer(colors=True),
            ],
            wrapper_class=structlog.stdlib.BoundLogger,
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True,
        )

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)

    logging.getLogger("survey_system").setLevel(level)

    _CONFIGURED = True
    structlog.get_logger(__name__).info(
        "logging_configured",
        log_json=settings.log_json,
        log_level=settings.log_level,
    )


def get_logger(name: str) -> BoundLogger:
    """Return a structlog-bound logger for the given name.

    Args:
        name: Logger name (typically ``__name__``).

    Returns:
        Configured :class:`structlog.stdlib.BoundLogger` instance.
    """
    return structlog.get_logger(name)


def reset_logging_configuration() -> None:
    """Reset internal logging configuration state (for tests)."""
    global _CONFIGURED
    _CONFIGURED = False
    reset_fn = getattr(structlog, "reset_defaults", None)
    if callable(reset_fn):
        reset_fn()
