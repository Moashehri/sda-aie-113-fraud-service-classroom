"""Structured logging with request trace correlation."""

import json
import logging
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

trace_id_context: ContextVar[str] = ContextVar("trace_id", default="system")

_SAFE_EXTRA_FIELDS = {
    "decision",
    "duration_ms",
    "event",
    "exception_type",
    "method",
    "model_version",
    "path",
    "probability_bucket",
    "status_code",
}


class JsonFormatter(logging.Formatter):
    """Serialize application log records as one JSON object per line."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "trace_id": getattr(record, "trace_id", trace_id_context.get()),
        }
        for field in _SAFE_EXTRA_FIELDS:
            if hasattr(record, field):
                payload[field] = getattr(record, field)
        return json.dumps(payload, separators=(",", ":"), default=str)


def configure_logging(level: str = "INFO") -> None:
    """Configure root and server loggers to emit structured JSON."""
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)

    for logger_name in ("uvicorn", "uvicorn.access", "uvicorn.error"):
        server_logger = logging.getLogger(logger_name)
        server_logger.handlers.clear()
        server_logger.propagate = True


def probability_bucket(probability: float) -> str:
    """Return a coarse bucket suitable for privacy-conscious logs."""
    if probability < 0.25:
        return "0.00-0.24"
    if probability < 0.50:
        return "0.25-0.49"
    if probability < 0.75:
        return "0.50-0.74"
    return "0.75-1.00"
