"""Métricas Prometheus del servicio: middleware propio sobre prometheus_client."""
import os
import time

from fastapi import FastAPI, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from starlette.middleware.base import BaseHTTPMiddleware

APP_NAME = os.getenv("APP_NAME", "reports-backend")
EXCLUDED_PATHS = {"/health", "/metrics"}  # las probes no deben llenar las gráficas

REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Total de requests HTTP",
    ["app", "method", "path"],
)
REQUESTS_BY_STATUS = Counter(
    "http_requests_by_status_total",
    "Requests HTTP por código de estado",
    ["app", "method", "path", "status_code"],
)
REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "Latencia de las requests en segundos",
    ["app", "method", "path"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10),
)
RESPONSE_SIZE = Histogram(
    "http_response_size_bytes",
    "Tamaño de las respuestas en bytes",
    ["app", "method", "path"],
    buckets=(100, 500, 1_000, 5_000, 10_000, 50_000, 100_000, 500_000, 1_000_000),
)


def _route_template(request: Request) -> str:
    """Devuelve /reportes/{reporte_id} y no /reportes/65a1...; así hay una serie por ruta, no por ID."""
    route = request.scope.get("route")
    return getattr(route, "path", None) or "unmatched"  # rutas inexistentes: una sola serie


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path in EXCLUDED_PATHS:
            return await call_next(request)

        start = time.perf_counter()
        status_code = 500  # si la app lanza una excepción sin respuesta, se cuenta como 500
        size = 0
        try:
            response = await call_next(request)
            status_code = response.status_code
            size = int(response.headers.get("content-length", 0))
            return response
        finally:
            method = request.method
            path = _route_template(request)  # se lee después: el router la llena al resolver la ruta
            REQUESTS_TOTAL.labels(APP_NAME, method, path).inc()
            REQUESTS_BY_STATUS.labels(APP_NAME, method, path, str(status_code)).inc()
            REQUEST_DURATION.labels(APP_NAME, method, path).observe(time.perf_counter() - start)
            RESPONSE_SIZE.labels(APP_NAME, method, path).observe(size)


def setup_metrics(app: FastAPI) -> None:
    app.add_middleware(MetricsMiddleware)

    @app.get("/metrics", include_in_schema=False)
    def metrics() -> Response:
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)