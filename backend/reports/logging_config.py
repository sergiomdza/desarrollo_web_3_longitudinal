"""Logging JSON estructurado: una línea por evento, en stdout.

Reemplaza los handlers de uvicorn y apaga su access log.
"""
import json
import logging
import logging.config
import os
import re
import time
from contextvars import ContextVar
from datetime import datetime, timezone

SERVICE_NAME = os.getenv("SERVICE_NAME", "reportes-analitica")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
EXCLUDED_PATHS = {"/health", "/metrics"}

# Contexto de la request en curso. Lo llena RequestContextMiddleware (middleware.py).
request_context: ContextVar[dict | None] = ContextVar("request_context", default=None)

# Atributos estándar de LogRecord (y de uvicorn) que NO se copian como contexto.
_RESERVED = set(logging.makeLogRecord({}).__dict__) | {"message", "asctime", "color_message"}
_URI_RE = re.compile(r"mongodb(?:\+srv)?://[^\s\"']+", re.IGNORECASE)


def redact(text: str) -> str:
    """Oculta cualquier URI de MongoDB que se cuele en un mensaje o error."""
    return _URI_RE.sub("mongodb://***", text)


class ContextFilter(logging.Filter):
    """Agrega method, path y duration_ms de la request actual y descarta /health y /metrics."""

    def filter(self, record: logging.LogRecord) -> bool:
        ctx = request_context.get()
        if ctx:
            if ctx["path"] in EXCLUDED_PATHS:
                return False
            if not hasattr(record, "method"):
                record.method = ctx["method"]
            if not hasattr(record, "path"):
                record.path = ctx["path"]
            if not hasattr(record, "duration_ms"):
                record.duration_ms = round((time.perf_counter() - ctx["start"]) * 1000, 2)
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "service": SERVICE_NAME,
            "message": redact(record.getMessage()),
        }
        for key, value in record.__dict__.items():
            if key not in _RESERVED and not key.startswith("_"):
                payload[key] = value
        if record.exc_info and record.exc_info[0] is not None:
            exc_type, exc, _ = record.exc_info
            payload["error"] = redact(f"{exc_type.__name__}: {exc}")
            payload["traceback"] = redact(self.formatException(record.exc_info))
        return json.dumps(payload, ensure_ascii=False, default=str)


def setup_logging() -> None:
    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "filters": {"context": {"()": ContextFilter}},
            "formatters": {"json": {"()": JsonFormatter}},
            "handlers": {
                "stdout": {
                    "class": "logging.StreamHandler",
                    "stream": "ext://sys.stdout",
                    "formatter": "json",
                    "filters": ["context"],
                }
            },
            "root": {"level": LOG_LEVEL, "handlers": ["stdout"]},
            "loggers": {
                # uvicorn trae handlers en texto plano: se vacían y se deja propagar al root.
                "uvicorn": {"handlers": [], "level": LOG_LEVEL, "propagate": True},
                "uvicorn.error": {"handlers": [], "level": LOG_LEVEL, "propagate": True},
                # access log por defecto: apagado por completo.
                "uvicorn.access": {"handlers": [], "level": "CRITICAL", "propagate": False},
            },
        }
    )
    logging.getLogger("uvicorn.access").disabled = True