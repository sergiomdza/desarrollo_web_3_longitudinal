"""Configuración de logging del servicio.

Todo lo que el servicio escribe en la salida estándar es JSON, una línea por
evento: nuestros logs de dominio, los de Uvicorn/FastAPI y los de cualquier
librería. Alloy lee esas líneas del contenedor y las manda a Loki.
"""

import json
import logging
import logging.config
import os
import re
import sys
import time
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any, Optional

from starlette.types import ASGIApp, Receive, Scope, Send

# En Kubernetes llegan por el ConfigMap; en local, por docker-compose.yaml.
# Tienen valor por defecto para que el servicio siempre pueda escribir logs.
SERVICE_NAME = os.environ.get("SERVICE_NAME", "categorias-ubicaciones")
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()

logger = logging.getLogger("categorias_ubicaciones")

# Atributos que Python pone en todo registro de log (name, levelname, lineno...).
# Lo que NO esté aquí llegó por `extra={...}` y es el contexto del evento.
ATRIBUTOS_ESTANDAR = set(logging.makeLogRecord({}).__dict__)

# Tampoco son contexto:
# - "message" y "asctime": los agrega Python si otro handler formatea el registro.
# - "color_message": lo agrega Uvicorn, es el mismo mensaje con colores de terminal.
ATRIBUTOS_IGNORADOS = ATRIBUTOS_ESTANDAR | {"message", "asctime", "color_message"}


def _sin_credenciales(texto: str) -> str:
    """Oculta cadenas de conexión de MongoDB para que nunca lleguen a los logs."""
    return re.sub(r"mongodb(\+srv)?://\S+", "mongodb://***", texto)


class JsonFormatter(logging.Formatter):
    """Convierte cada registro de log en una sola línea JSON."""

    def format(self, record: logging.LogRecord) -> str:
        momento = datetime.fromtimestamp(record.created, tz=timezone.utc)

        evento = {
            "timestamp": momento.isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "service": SERVICE_NAME,
            "logger": record.name,
            "message": _sin_credenciales(record.getMessage()),
        }

        # Contexto del evento: lo que se pasó en extra={...} (activo_id, status_code...)
        for nombre, valor in record.__dict__.items():
            if nombre not in ATRIBUTOS_IGNORADOS:
                evento[nombre] = valor

        # Si hubo una excepción, su causa va en el mismo registro y no en líneas sueltas
        if record.exc_info:
            traceback = self.formatException(record.exc_info)
            evento["exception"] = _sin_credenciales(traceback)

        return json.dumps(evento, ensure_ascii=False, default=str)


# --- Contexto de la request ---------------------------------------------------
# El middleware guarda aquí la request que se está atendiendo. Un ContextVar es
# propio de cada request (aunque se atiendan varias a la vez), y el filtro lo
# lee para agregar method, path y duration_ms a todo log emitido durante ella.
# Así los endpoints solo pasan el contexto de dominio (activo_id, codigo...).
_request_actual: ContextVar[Optional[dict[str, Any]]] = ContextVar("request_actual", default=None)

SIN_RUTA = "sin_ruta"


class ContextoRequestMiddleware:
    """Middleware ASGI que marca el inicio de cada request para los logs."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        token = _request_actual.set({"scope": scope, "inicio": time.perf_counter()})
        try:
            await self.app(scope, receive, send)
        finally:
            _request_actual.reset(token)


class ContextoRequestFilter(logging.Filter):
    """Agrega method, path y duration_ms a los logs emitidos durante una request."""

    def filter(self, record: logging.LogRecord) -> bool:
        contexto = _request_actual.get()
        if contexto is None:  # log fuera de una request (arranque, apagado...)
            return True

        scope = contexto["scope"]
        # FastAPI deja en el scope la ruta que atendió la request. Se usa su
        # PLANTILLA (/activos/{activo_id}), igual que en las métricas.
        ruta = scope.get("route")
        valores = {
            "method": scope["method"],
            "path": getattr(ruta, "path", SIN_RUTA),
            "duration_ms": round((time.perf_counter() - contexto["inicio"]) * 1000, 2),
        }
        for nombre, valor in valores.items():
            if not hasattr(record, nombre):  # lo que venga en extra={...} tiene prioridad
                setattr(record, nombre, valor)
        return True


LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {"()": JsonFormatter},
    },
    "filters": {
        "contexto_request": {"()": ContextoRequestFilter},
    },
    "handlers": {
        "stdout": {
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
            "formatter": "json",
            "filters": ["contexto_request"],
        },
    },
    # Todos los loggers terminan en el root: un solo handler y un solo formato.
    "root": {"handlers": ["stdout"], "level": LOG_LEVEL},
    "loggers": {
        # Uvicorn trae sus propios handlers de texto plano. Se los quitamos y
        # dejamos que sus mensajes suban al root para que salgan en JSON.
        "uvicorn": {"handlers": [], "level": LOG_LEVEL, "propagate": True},
        "uvicorn.error": {"handlers": [], "level": LOG_LEVEL, "propagate": True},
        # Access log apagado: sin handlers y sin propagar, Uvicorn ni lo genera.
        # Es una línea por cada request (incluyendo /health y /metrics): puro ruido.
        "uvicorn.access": {"handlers": [], "propagate": False},
    },
}


def _registrar_error_fatal(tipo, error, traza) -> None:
    """Registra en JSON el error que está por tumbar el proceso."""
    logger.critical(
        "Error fatal: el servicio se detiene",
        exc_info=(tipo, error, traza),
    )


def configurar_logging() -> None:
    """Aplica la configuración. Se llama una sola vez, al arrancar el servicio."""
    logging.config.dictConfig(LOGGING_CONFIG)

    # Los warnings de Python salen en texto plano por stderr: que pasen por logging.
    logging.captureWarnings(True)

    # Un error no capturado imprime su traceback en texto plano: que salga en JSON.
    sys.excepthook = _registrar_error_fatal
