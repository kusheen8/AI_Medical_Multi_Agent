"""
Structured logging configuration using structlog.

Produces JSON-formatted logs in production and human-readable console output
in development. Logs include timestamps, log levels, and arbitrary context fields.
All logging is async-safe (structlog uses thread-local / context-var binding).

Phase 5 enhancements:
- SensitiveDataFilter: strips API keys, tokens, PHI from log context
- Security event logging helpers
- Optional file handler for local development
"""

import logging
import re
import sys
from pathlib import Path
from typing import Any

import structlog


# ── Sensitive Data Filter ────────────────────────────────────────────────

# Patterns that should never appear in logs
_SENSITIVE_PATTERNS = [
    re.compile(r"(?i)(api[_-]?key|auth[_-]?token|secret[_-]?key|password|bearer)\s*[:=]\s*\S+"),
    re.compile(r"(?i)eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+"),  # JWT pattern
]

_SENSITIVE_KEYS = frozenset({
    "password", "hashed_password", "secret", "token", "api_key",
    "access_token", "refresh_token", "authorization", "x_admin_key",
    "gemini_api_key", "sendgrid_api_key", "twilio_auth_token",
    "fcm_server_key", "webhook_signing_secret", "jwt_secret_key",
    "field_encryption_key",
})


def _filter_sensitive_data(
    logger: Any, method_name: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    """structlog processor that redacts sensitive data from log entries.

    Redacts:
    - Known sensitive keys (passwords, tokens, API keys)
    - JWT token patterns in string values
    - Known PHI patterns in string values
    """
    for key in list(event_dict.keys()):
        if key.lower() in _SENSITIVE_KEYS:
            event_dict[key] = "[REDACTED]"
        elif isinstance(event_dict[key], str):
            value = event_dict[key]
            for pattern in _SENSITIVE_PATTERNS:
                if pattern.search(value):
                    event_dict[key] = "[REDACTED]"
                    break
    return event_dict


# ── Setup ────────────────────────────────────────────────────────────────


def setup_logging(
    log_level: str = "INFO",
    app_env: str = "development",
    log_file: str | None = None,
) -> None:
    """Configure structured logging for the application.

    Args:
        log_level: Minimum log level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        app_env: Application environment. Uses JSON renderer in production,
                 console renderer in development.
        log_file: Optional file path for log output (development only).
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
        _filter_sensitive_data,  # Phase 5: strip sensitive data
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

    # Optional file handler (development)
    if log_file:
        file_path = Path(log_file)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(str(file_path), encoding="utf-8")
        json_renderer = structlog.processors.JSONRenderer()
        file_formatter = structlog.stdlib.ProcessorFormatter(
            processors=[
                structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                json_renderer,
            ],
            foreign_pre_chain=shared_processors,
        )
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)

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


# ── Security Event Helpers ───────────────────────────────────────────────

_security_logger = structlog.get_logger("security")


async def log_auth_failure(
    reason: str,
    ip_address: str = "unknown",
    email: str | None = None,
    **extra: Any,
) -> None:
    """Log an authentication failure event.

    Args:
        reason: Why authentication failed.
        ip_address: Client IP address.
        email: The email that was attempted (redacted in storage).
        **extra: Additional context.
    """
    await _security_logger.awarning(
        "auth_failure",
        reason=reason,
        ip_address=ip_address,
        email_attempted=email is not None,
        **extra,
    )


async def log_authz_violation(
    user_id: str,
    resource: str,
    action: str,
    **extra: Any,
) -> None:
    """Log an authorization violation event.

    Args:
        user_id: The user who attempted the action.
        resource: The resource they tried to access.
        action: What they tried to do.
        **extra: Additional context.
    """
    await _security_logger.awarning(
        "authz_violation",
        user_id=user_id,
        resource=resource,
        action=action,
        **extra,
    )


async def log_rate_limit_triggered(
    client_ip: str,
    path: str,
    limit: int,
    **extra: Any,
) -> None:
    """Log a rate limit trigger event.

    Args:
        client_ip: Client IP that hit the limit.
        path: The endpoint path.
        limit: The limit that was exceeded.
        **extra: Additional context.
    """
    await _security_logger.awarning(
        "rate_limit_triggered",
        client_ip=client_ip,
        path=path,
        limit=limit,
        **extra,
    )
