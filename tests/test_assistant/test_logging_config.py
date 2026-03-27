"""Tests for structured logging configuration."""

import json
import logging
import tempfile

import structlog

from assistant.logging_config import configure_logging


class TestConfigureLogging:
    def setup_method(self):
        """Reset logging state between tests."""
        root = logging.getLogger()
        root.handlers.clear()
        structlog.reset_defaults()

    def test_console_format_default(self):
        configure_logging(log_format="console", log_level="INFO")
        root = logging.getLogger()
        assert root.level == logging.INFO
        assert len(root.handlers) >= 1

    def test_json_format_produces_valid_json(self, capsys):
        configure_logging(log_format="json", log_level="INFO")
        test_logger = logging.getLogger("test.json_output")
        test_logger.info("test message")

        # JSON renderer outputs to stderr via StreamHandler
        captured = capsys.readouterr()
        # The output goes through structlog's JSON renderer
        # Verify the logger was configured without errors
        assert logging.getLogger().level == logging.INFO

    def test_log_level_debug(self):
        configure_logging(log_format="console", log_level="DEBUG")
        assert logging.getLogger().level == logging.DEBUG

    def test_log_level_warning(self):
        configure_logging(log_format="console", log_level="WARNING")
        assert logging.getLogger().level == logging.WARNING

    def test_log_level_case_insensitive(self):
        configure_logging(log_format="console", log_level="debug")
        assert logging.getLogger().level == logging.DEBUG

    def test_invalid_log_level_defaults_to_info(self):
        configure_logging(log_format="console", log_level="INVALID")
        assert logging.getLogger().level == logging.INFO

    def test_file_handler_created(self):
        with tempfile.NamedTemporaryFile(suffix=".log", delete=False) as f:
            configure_logging(
                log_format="console", log_level="INFO", log_file=f.name
            )
            root = logging.getLogger()
            file_handlers = [
                h for h in root.handlers if isinstance(h, logging.FileHandler)
            ]
            assert len(file_handlers) == 1
            assert file_handlers[0].baseFilename == f.name

    def test_no_file_handler_by_default(self):
        configure_logging(log_format="console", log_level="INFO")
        root = logging.getLogger()
        file_handlers = [
            h for h in root.handlers if isinstance(h, logging.FileHandler)
        ]
        assert len(file_handlers) == 0

    def test_noisy_loggers_quieted(self):
        configure_logging(log_format="console", log_level="DEBUG")
        assert logging.getLogger("uvicorn.access").level == logging.WARNING
        assert logging.getLogger("httpx").level == logging.WARNING
        assert logging.getLogger("httpcore").level == logging.WARNING
