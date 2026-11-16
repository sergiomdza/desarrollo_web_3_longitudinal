"""Métricas HTTP del servicio en formato Prometheus.

Expone 4 métricas:

- http_requests_total            (Counter)   labels: method, path
- http_responses_total           (Counter)   labels: path, status_code
- http_request_duration_seconds  (Histogram) labels: method, path
- http_response_size_bytes       (Histogram) labels: method, path

`path` es siempre la ruta PLANTILLA de FastAPI (por ejemplo
"/activos/{activo_id}"), nunca el ID real: así hay una serie por endpoint y no
una por activo. Las rutas que no existen se registran como "sin_ruta".

Uso en main.py (2 líneas):

    from metrics import instrumentar
    instrumentar(app)
"""

import time

from fastapi import FastAPI, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from starlette.routing import Match
from starlette.types import ASGIApp, Message, Receive, Scope, Send

SIN_RUTA = "sin_ruta"

HTTP_REQUESTS = Counter(
    "http_requests_total",
    "Total de requests HTTP recibidas.",
    ["method", "path"],
)

HTTP_RESPONSES = Counter(
    "http_responses_total",
    "Total de respuestas HTTP enviadas, por código de estado.",
    ["path", "status_code"],
)

HTTP_REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "Tiempo que tarda el servicio en responder una request, en segundos.",
    ["method", "path"],
)

HTTP_RESPONSE_SIZE = Histogram(
    "http_response_size_bytes",
    "Tamaño del cuerpo de la respuesta, en bytes.",
    ["method", "path"],
    buckets=(100, 500, 1_000, 5_000, 10_000, 50_000, 100_000),
)


def _ruta_plantilla(app: ASGIApp, scope: Scope) -> str:
    """Devuelve la ruta plantilla que atiende la request, o "sin_ruta"."""
    for route in getattr(app, "routes", []):
        match, _ = route.matches(scope)
        if match == Match.FULL:
            return route.path
    return SIN_RUTA


class MetricsMiddleware:
    """Middleware ASGI que mide cada request: conteo, status, duración y bytes."""

    def __init__(self, app: ASGIApp, routes_app: FastAPI) -> None:
        self.app = app
        # La app de FastAPI, para buscar la ruta plantilla en sus rutas.
        self.routes_app = routes_app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        method = scope["method"]
        path = _ruta_plantilla(self.routes_app, scope)
        HTTP_REQUESTS.labels(method=method, path=path).inc()

        status_code = 500  # si la app revienta sin responder, cuenta como 500
        response_size = 0
        inicio = time.perf_counter()

        async def send_y_medir(message: Message) -> None:
            nonlocal status_code, response_size
            if message["type"] == "http.response.start":
                status_code = message["status"]
            elif message["type"] == "http.response.body":
                response_size += len(message.get("body", b""))
            await send(message)

        try:
            await self.app(scope, receive, send_y_medir)
        finally:
            HTTP_REQUEST_DURATION.labels(method=method, path=path).observe(
                time.perf_counter() - inicio
            )
            HTTP_RESPONSE_SIZE.labels(method=method, path=path).observe(response_size)
            HTTP_RESPONSES.labels(path=path, status_code=str(status_code)).inc()


def metrics_endpoint(request: Request) -> Response:
    """GET /metrics: todas las métricas en el formato de texto de Prometheus."""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


def instrumentar(app: FastAPI) -> None:
    """Registra el middleware de métricas y la ruta /metrics en la app."""
    app.add_middleware(MetricsMiddleware, routes_app=app)
    app.add_route("/metrics", metrics_endpoint, methods=["GET"], include_in_schema=False)
