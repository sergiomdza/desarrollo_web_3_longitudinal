"""Métricas Prometheus del servicio (ver "contrato de observabilidad" en README).

- http_requests_total{app, method, handler, status}      -> Counter
- http_request_duration_seconds{app, method, handler}    -> Histogram (s)
- http_response_size_bytes{app, method, handler}         -> Histogram (bytes)

`handler` es la ruta como plantilla (/requests/{id}), no la URL real, para no
crear una serie por cada ID. /health y /metrics no se miden.
"""

import os
import time

from fastapi import FastAPI, Request, Response
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Histogram,
    disable_created_metrics,
    generate_latest,
)
APP_NAME = os.getenv("SERVICE_NAME", "requests-backend")
EXCLUDED_PATHS = {"/health", "/metrics"}

# Sin esto, prometheus_client publica series extra *_created por cada métrica.
disable_created_metrics()

REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Total de requests HTTP por método, ruta y status code exacto.",
    ["app", "method", "handler", "status"],
)

# Buckets finos: el servicio responde en milisegundos, y con los buckets por
# defecto (el primero en 0.1 s) todos los percentiles caen en el mismo bucket.
REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "Latencia de las requests HTTP en segundos.",
    ["app", "method", "handler"],
    buckets=(0.001, 0.0025, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5),
)

RESPONSE_SIZE = Histogram(
    "http_response_size_bytes",
    "Tamaño del cuerpo de las respuestas HTTP en bytes.",
    ["app", "method", "handler"],
    buckets=(50, 100, 250, 500, 1_000, 2_500, 5_000, 10_000, 50_000, 100_000),
)


def _route_template(request: Request) -> str:
    """Plantilla de la ruta (/requests/{id}) o "none" si ninguna ruta coincidió.

    FastAPI guarda en scope["route"] la ruta que hizo match al enrutar, por eso
    se lee después de call_next (antes de eso todavía no existe)."""
    route = request.scope.get("route")
    return getattr(route, "path", "none")


def setup_metrics(app: FastAPI) -> None:
    """Registra el middleware de métricas y el endpoint /metrics."""

    @app.middleware("http")
    async def prometheus_middleware(request: Request, call_next):
        if request.url.path in EXCLUDED_PATHS:
            return await call_next(request)

        method = request.method
        start = time.perf_counter()
        status_code = 500  # si la ruta lanza una excepción no controlada
        size = 0

        try:
            response = await call_next(request)
            status_code = response.status_code
            size = int(response.headers.get("content-length", 0))
            return response
        finally:
            handler = _route_template(request)
            REQUESTS_TOTAL.labels(APP_NAME, method, handler, str(status_code)).inc()
            REQUEST_DURATION.labels(APP_NAME, method, handler).observe(
                time.perf_counter() - start
            )
            RESPONSE_SIZE.labels(APP_NAME, method, handler).observe(size)

    @app.get("/metrics", include_in_schema=False)
    def metrics() -> Response:
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
