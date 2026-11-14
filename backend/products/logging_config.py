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
from datetime import datetime, timezone

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
