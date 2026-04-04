"""Structured logging configuration using structlog."""

import logging
import sys

import structlog


def configure_logging(
    log_format: str = "console",
    log_level: str = "INFO",
    log_file: str | None = None,
) -> None:
    """Configure structured logging for the application.

    Args:
        log_format: Output format — "json" for production, "console" for development.
        log_level: Root log level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        log_file: Optional file path to write logs to.
    """
    level = getattr(logging, log_level.upper(), logging.INFO)

    # Shared processors for both stdlib and structlog
    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    # Disable colors when stderr is not a TTY (e.g., redirected to a log file)
    use_colors = sys.stderr.isatty()

    if log_format == "json":
        renderer: structlog.types.Processor = structlog.processors.JSONRenderer()
        file_renderer: structlog.types.Processor = renderer
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=use_colors)
        file_renderer = structlog.dev.ConsoleRenderer(colors=False)

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
    )

    # Root logger setup
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Clear existing handlers
    root_logger.handlers.clear()

    # Console handler
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Optional file handler (no ANSI color codes)
    if log_file:
        file_formatter = structlog.stdlib.ProcessorFormatter(
            processors=[
                structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                file_renderer,
            ],
        )
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)

    # Quiet noisy third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
