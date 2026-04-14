"""
Structured logging configuration using structlog.

Produces JSON-formatted logs in production and human-readable console output
in development. Logs include timestamps, log levels, and arbitrary context fields.
All logging is async-safe (structlog uses thread-local / context-var binding).
"""

import logging
import sys
from typing import Any

import structlog


def setup_logging(log_level: str = "INFO", app_env: str = "development") -> None:
    """Configure structured logging for the application.

    Args:
        log_level: Minimum log level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        app_env: Application environment. Uses JSON renderer in production,
                 console renderer in development.
    """
    # Determine renderer based on environment
    renderer: Any
    if app_env == "production":
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    # Shared processors for both structlog and stdlib logging
    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    # Configure structlog
    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Configure stdlib logging to use structlog formatting
    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
        foreign_pre_chain=shared_processors,
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # Quiet noisy third-party loggers
    for noisy_logger in ("uvicorn.access", "uvicorn.error", "motor", "pymongo"):
        logging.getLogger(noisy_logger).setLevel(logging.WARNING)


def get_logger(name: str | None = None) -> Any:
    """Get a bound structlog logger instance.

    Args:
        name: Logger name (typically __name__ of the calling module).

    Returns:
        A bound structlog logger with context variable support.
    """
    return structlog.get_logger(name)
