"""Configuración de logs en formato JSON para el módulo de Auditorías.

Cada evento se escribe en stdout como un objeto JSON en una sola línea, para
que Alloy lo recoja del contenedor y lo envíe a Loki.

Campos de cada registro:
    timestamp  fecha y hora en UTC (ISO 8601 con milisegundos)
    level      INFO, WARNING, ERROR...
    service    nombre del servicio (variable SERVICE_NAME, por defecto audits-api)
    logger     logger que generó el evento (app, uvicorn.error...)
    message    descripción del evento
    error      solo si hay una excepción: tipo, mensaje y traceback en el mismo registro
    ...        cualquier campo de contexto que se pase con ``extra``

Uso desde el código:

    from app.logging_config import get_logger

    logger = get_logger(__name__)
    logger.info("Auditoría creada", extra={"auditoria_id": 5})

    -> {"timestamp": "...", "level": "INFO", "service": "audits-api",
        "logger": "app.main", "message": "Auditoría creada", "auditoria_id": 5}

Los loggers de Uvicorn (``uvicorn`` y ``uvicorn.error``) se redirigen a este
mismo formato, y el access log (``uvicorn.access``, una línea por cada request)
se desactiva porque solo genera ruido.
"""

import json
import logging
import logging.config
import os
import re
import sys
import threading
import traceback
from datetime import datetime, timezone

SERVICE_NAME = os.getenv("SERVICE_NAME", "audits-api")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

# Atributos propios de LogRecord: todo lo que no esté aquí llegó por ``extra``
# y se agrega como campo de contexto del JSON.
_RESERVED_ATTRS = frozenset(vars(logging.makeLogRecord({}))) | {
    "message",
    "asctime",
    "taskName",
    "color_message",  # uvicorn lo agrega con códigos de color de terminal
}

# Oculta usuario y contraseña de URIs de MongoDB si llegaran a un mensaje.
_MONGO_CREDENTIALS = re.compile(r"(mongodb(?:\+srv)?://)[^@/\s]+@", re.IGNORECASE)


def _redact(text: str) -> str:
    return _MONGO_CREDENTIALS.sub(r"\1***:***@", text)


class JsonFormatter(logging.Formatter):
    """Convierte cada LogRecord en una línea JSON."""

    def format(self, record: logging.LogRecord) -> str:
        log = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc)
            .isoformat(timespec="milliseconds")
            .replace("+00:00", "Z"),
            "level": record.levelname,
            "service": SERVICE_NAME,
            "logger": record.name,
            "message": _redact(record.getMessage()).strip(),
        }

        for key, value in record.__dict__.items():
            if key not in _RESERVED_ATTRS and not key.startswith("_"):
                log[key] = value

        if record.exc_info and record.exc_info[0] is not None:
            exc_type, exc_value, exc_tb = record.exc_info
            log["error"] = {
                "type": exc_type.__name__,
                "message": _redact(str(exc_value)),
                "stacktrace": _redact("".join(traceback.format_exception(exc_type, exc_value, exc_tb))),
            }

        # default=str: datetimes, ObjectId, etc. se serializan como texto.
        # json.dumps escapa los saltos de línea, así que siempre es una sola línea.
        return json.dumps(log, ensure_ascii=False, default=str)


LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {"()": JsonFormatter},
    },
    "handlers": {
        "stdout": {
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
            "formatter": "json",
        },
    },
    # Todos los loggers (app, fastapi, pymongo...) terminan en el root.
    "root": {"level": LOG_LEVEL, "handlers": ["stdout"]},
    "loggers": {
        # Uvicorn trae sus propios handlers en texto plano; se los quitamos
        # para que sus mensajes (arranque, apagado, errores) suban al root en JSON.
        "uvicorn": {"handlers": [], "propagate": True, "level": LOG_LEVEL},
        "uvicorn.error": {"handlers": [], "propagate": True, "level": LOG_LEVEL},
        # Access log: una línea por request, incluidas /health y /metrics. No se usa.
        "uvicorn.access": {"handlers": [], "propagate": False},
        # pymongo es muy verboso en DEBUG y podría mostrar datos de conexión.
        "pymongo": {"level": "WARNING"},
    },
}


def _log_uncaught(exc_type, exc_value, exc_tb) -> None:
    """Excepciones no atrapadas (p. ej. falta MONGO_URI al arrancar) también en JSON."""
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_tb)
        return
    logging.getLogger("app").critical(
        "Excepción no controlada, el servicio se detiene",
        exc_info=(exc_type, exc_value, exc_tb),
    )


def _log_uncaught_thread(args: threading.ExceptHookArgs) -> None:
    if args.exc_type is SystemExit:
        return
    logging.getLogger("app").error(
        "Excepción no controlada en un hilo",
        exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
        extra={"thread_name": args.thread.name if args.thread else None},
    )


def setup_logging() -> None:
    """Aplica la configuración. Se llama una vez al importar app.main."""
    logging.config.dictConfig(LOGGING_CONFIG)
    logging.getLogger("uvicorn.access").disabled = True
    logging.captureWarnings(True)  # warnings.warn(...) también como JSON
    sys.excepthook = _log_uncaught
    threading.excepthook = _log_uncaught_thread


def get_logger(name: str = "app") -> logging.Logger:
    return logging.getLogger(name)
