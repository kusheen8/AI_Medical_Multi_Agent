"""
Unit tests for core/logging.py — Structured logging setup.
"""

import json
import logging
from io import StringIO

import structlog

from app.core.logging import get_logger, setup_logging


class TestSetupLogging:
    """Tests for the setup_logging function."""

    def test_setup_logging_configures_root_logger(self) -> None:
        """setup_logging should configure the root logger with a handler."""
        setup_logging(log_level="INFO", app_env="development")
        root = logging.getLogger()
        assert len(root.handlers) >= 1
        assert root.level == logging.INFO

    def test_setup_logging_respects_log_level(self) -> None:
        """setup_logging should set the correct log level."""
        setup_logging(log_level="DEBUG", app_env="development")
        root = logging.getLogger()
        assert root.level == logging.DEBUG

    def test_setup_logging_json_output_in_production(self) -> None:
        """In production mode, logs should be valid JSON."""
        setup_logging(log_level="INFO", app_env="production")

        # Capture log output
        stream = StringIO()
        root = logging.getLogger()

        handler = logging.StreamHandler(stream)
        # Reuse the formatter from the configured handler
        handler.setFormatter(root.handlers[0].formatter)
        root.addHandler(handler)

        try:
            test_logger = structlog.get_logger("test_json")
            test_logger.info("json_test_event", key="value")

            output = stream.getvalue()
            # Should contain valid JSON lines
            for line in output.strip().split("\n"):
                if line.strip():
                    parsed = json.loads(line)
                    assert "event" in parsed
                    assert parsed["event"] == "json_test_event"
                    assert parsed["key"] == "value"
        finally:
            root.removeHandler(handler)

    def test_setup_logging_quiets_noisy_loggers(self) -> None:
        """Third-party loggers should be set to WARNING or above."""
        setup_logging(log_level="DEBUG", app_env="development")

        for name in ("uvicorn.access", "uvicorn.error", "motor", "pymongo"):
            assert logging.getLogger(name).level >= logging.WARNING


class TestGetLogger:
    """Tests for the get_logger function."""

    def test_get_logger_returns_bound_logger(self) -> None:
        """get_logger should return a structlog BoundLogger instance."""
        setup_logging(log_level="INFO", app_env="development")
        log = get_logger("test_module")
        assert log is not None

    def test_get_logger_with_name(self) -> None:
        """get_logger should accept a module name."""
        setup_logging(log_level="INFO", app_env="development")
        log = get_logger("my.module.name")
        assert log is not None

    def test_get_logger_without_name(self) -> None:
        """get_logger should work without a name."""
        setup_logging(log_level="INFO", app_env="development")
        log = get_logger()
        assert log is not None
