"""Observabilidad del servicio de Notificaciones.

- Logs estructurados: todo sale a stdout en JSON, una línea por evento
  (incluidos los mensajes de Uvicorn/FastAPI), con timestamp, level,
  service, message y el contexto de la petición en curso.
- Métricas Prometheus en GET /metrics:
    * http_requests_total            -> total de requests y por status_code
    * http_request_duration_seconds  -> latencia (histograma)
    * http_response_size_bytes       -> tamaño de las respuestas (histograma)
- /health y /metrics no generan métricas ni logs (son ruido: las probes de
  Kubernetes y el scrape de Prometheus los llaman cada pocos segundos).
"""

import json
import logging
import logging.config
import os
import socket
import traceback
from contextvars import ContextVar
from datetime import datetime, timezone
from time import perf_counter

from prometheus_client import Counter, Histogram


SERVICE_NAME = os.getenv("SERVICE_NAME", "notificaciones")
POD_NAME = os.getenv("POD_NAME", socket.gethostname())

# Rutas que no se loggean ni se miden.
EXCLUDED_PATHS = {"/health", "/metrics"}

# Contexto de la petición actual (método, ruta...). Se agrega a cada log
# que se emita mientras se atiende esa petición.
request_context: ContextVar[dict] = ContextVar("request_context", default={})

logger = logging.getLogger("notificaciones")


# ---------------------------------------------------------------------------
# Logs en JSON
# ---------------------------------------------------------------------------

# Atributos estándar de LogRecord: no se copian al JSON como "extra".
_RESERVED = set(
    logging.LogRecord("", 0, "", 0, "", None, None).__dict__
) | {"message", "asctime", "color_message", "taskName"}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.fromtimestamp(
                record.created, timezone.utc
            ).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "service": SERVICE_NAME,
            "pod": POD_NAME,
            "logger": record.name,
            "message": record.getMessage(),
        }

        payload.update(request_context.get())

        for key, value in record.__dict__.items():
            if key not in _RESERVED and not key.startswith("_"):
                payload[key] = value

        if record.exc_info and record.exc_info[0] is not None:
            exc_type, exc_value, exc_tb = record.exc_info
            payload["error"] = {
                "type": exc_type.__name__,
                "detail": str(exc_value),
                "traceback": "".join(
                    traceback.format_exception(exc_type, exc_value, exc_tb)
                ),
            }

        return json.dumps(payload, ensure_ascii=False, default=str)


LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {"()": JsonFormatter},
    },
    "handlers": {
        "stdout": {
            "class": "logging.StreamHandler",
            "formatter": "json",
            "stream": "ext://sys.stdout",
        },
    },
    "root": {"handlers": ["stdout"], "level": "INFO"},
    "loggers": {
        # Los mensajes de Uvicorn pasan por el root (JSON).
        "uvicorn": {"handlers": [], "level": "INFO", "propagate": True},
        "uvicorn.error": {"handlers": [], "level": "INFO", "propagate": True},
        # El access log de Uvicorn se apaga: cada petición ya se loggea en
        # JSON desde ObservabilityMiddleware (y sin /health ni /metrics).
        "uvicorn.access": {"handlers": [], "level": "WARNING", "propagate": False},
        "pymongo": {"level": "WARNING"},
    },
}


def configure_logging() -> None:
    logging.config.dictConfig(LOGGING_CONFIG)


# ---------------------------------------------------------------------------
# Métricas
# ---------------------------------------------------------------------------

HTTP_REQUESTS = Counter(
    "http_requests_total",
    "Total de peticiones HTTP atendidas.",
    ["method", "handler", "status_code"],
)

HTTP_LATENCY = Histogram(
    "http_request_duration_seconds",
    "Latencia de las peticiones HTTP en segundos.",
    ["method", "handler"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10),
)

HTTP_RESPONSE_SIZE = Histogram(
    "http_response_size_bytes",
    "Tamaño de las respuestas HTTP en bytes.",
    ["method", "handler"],
    buckets=(0, 64, 128, 256, 512, 1024, 2048, 4096, 8192, 16384, 65536),
)


# ---------------------------------------------------------------------------
# Middleware ASGI: mide y loggea cada petición
# ---------------------------------------------------------------------------

class ObservabilityMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["path"] in EXCLUDED_PATHS:
            await self.app(scope, receive, send)
            return

        method = scope["method"]
        token = request_context.set({"method": method, "path": scope["path"]})

        status_code = 500
        response_size = 0
        response_started = False
        error = None
        start = perf_counter()

        async def send_wrapper(message):
            nonlocal status_code, response_size, response_started
            if message["type"] == "http.response.start":
                response_started = True
                status_code = message["status"]
            elif message["type"] == "http.response.body":
                response_size += len(message.get("body", b""))
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception as exc:  # error no controlado -> 500 con la causa en el log
            error = exc
            status_code = 500
            if not response_started:
                body = b'{"detail":"Error interno del servidor."}'
                response_size = len(body)
                await send({
                    "type": "http.response.start",
                    "status": 500,
                    "headers": [
                        (b"content-type", b"application/json"),
                        (b"content-length", str(len(body)).encode()),
                    ],
                })
                await send({"type": "http.response.body", "body": body})
            else:
                raise
        finally:
            duration = perf_counter() - start

            # Ruta "plantilla" (/notificaciones/{notification_id}) para que
            # cada ID no cree una serie nueva en Prometheus.
            route = scope.get("route")
            handler = getattr(route, "path", None) or "sin_ruta"

            HTTP_REQUESTS.labels(method, handler, str(status_code)).inc()
            HTTP_LATENCY.labels(method, handler).observe(duration)
            HTTP_RESPONSE_SIZE.labels(method, handler).observe(response_size)

            if status_code >= 500:
                level = logging.ERROR
            elif status_code >= 400:
                level = logging.WARNING
            else:
                level = logging.INFO

            logger.log(
                level,
                "Petición atendida" if error is None else "Error no controlado",
                exc_info=(type(error), error, error.__traceback__) if error else None,
                extra={
                    "route": handler,
                    "status_code": status_code,
                    "duration_ms": round(duration * 1000, 2),
                    "response_size_bytes": response_size,
                },
            )
            request_context.reset(token)
