"""Centralized logging with OpenTelemetry trace-log correlation."""

from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler

from opentelemetry import trace

LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
DEFAULT_LOG_FILE = os.path.join(LOG_DIR, "app.log")

_initialized = False


class _PresidioLanguageFilter(logging.Filter):
    """Drop noisy 'language is not supported by registry' warnings from Presidio."""

    def filter(self, record: logging.LogRecord) -> bool:
        return "language is not supported by registry" not in record.getMessage()


class _PresidioCardinalFilter(logging.Filter):
    """Drop 'Entity CARDINAL is not mapped' warnings from Presidio."""

    def filter(self, record: logging.LogRecord) -> bool:
        return "is not mapped to a Presidio entity" not in record.getMessage()


class TraceContextFormatter(logging.Formatter):
    """Formatter that injects OTel trace_id and span_id into every log record."""

    def format(self, record: logging.LogRecord) -> str:
        span = trace.get_current_span()
        ctx = span.get_span_context()
        if ctx and ctx.trace_id:
            record.trace_id = format(ctx.trace_id, "032x")
            record.span_id = format(ctx.span_id, "016x")
        else:
            record.trace_id = "0" * 32
            record.span_id = "0" * 16
        return super().format(record)


def setup_logging() -> None:
    """Configure application logging.

    Reads from environment variables:
        LOG_LEVEL: Logging level (default: INFO)
        LOG_FILE:  Path to log file (default: logs/app.log)
    """
    global _initialized
    if _initialized:
        return
    _initialized = True

    level = os.environ.get("LOG_LEVEL", "INFO").upper()
    log_file = os.environ.get("LOG_FILE", DEFAULT_LOG_FILE)
    os.makedirs(os.path.dirname(log_file), exist_ok=True)

    fmt = "%(asctime)s [%(levelname)s] %(name)s [trace=%(trace_id)s span=%(span_id)s] %(message)s"
    formatter = TraceContextFormatter(fmt)

    # Stderr handler
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)

    # Rotating file handler (10 MB, 5 backups)
    file_handler = RotatingFileHandler(
        log_file, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(level)
    root.addHandler(stream_handler)
    root.addHandler(file_handler)

    # Quiet noisy third-party loggers (NeMo internals, LangChain, httpx)
    for noisy in (
        "nemoguardrails",
        "langchain",
        "openai",
        "httpx",
        "httpcore",
        "presidio-analyzer",
    ):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    # Suppress specific noisy Presidio warnings
    presidio_logger = logging.getLogger("presidio-analyzer")
    presidio_logger.addFilter(_PresidioLanguageFilter())
    presidio_logger.addFilter(_PresidioCardinalFilter())


def get_logger(name: str) -> logging.Logger:
    """Return a named logger."""
    return logging.getLogger(name)
