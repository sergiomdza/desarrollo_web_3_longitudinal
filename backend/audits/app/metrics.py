"""
Instrumentación Prometheus del servicio de Auditorías.

Métricas expuestas en /metrics (todas con plantilla de ruta, p. ej. /auditorias/{id},
nunca con el ID concreto, para no crear una serie por cada auditoría):

  1. http_requests_total                  (Counter)   -> handler, method, status
       Sirve para "Total de requests" (por método y ruta) y
       "Requests por status code" (por ruta y status_code: 200, 201, 404, 422...).
  2. http_request_duration_seconds        (Histogram) -> handler, method
       Latencia en segundos; con histogram_quantile() se sacan p50/p95/p99.
  3. http_requests_inprogress             (Gauge)     -> handler, method
       Requests que se están atendiendo en este momento.
  4. http_response_size_bytes             (Histogram) -> handler, method
       Tamaño de las respuestas en bytes. La librería lo trae como Summary,
       pero el proyecto lo pide como histograma, por eso se define aquí.

/health y /metrics se excluyen para no ensuciar las métricas.
"""

from typing import Callable

from prometheus_client import REGISTRY, Histogram
from prometheus_fastapi_instrumentator import Instrumentator, metrics
from prometheus_fastapi_instrumentator.metrics import Info

# Rutas que no se miden (regex, como las espera el Instrumentator).
EXCLUDED_HANDLERS = ["^/health$", "^/metrics$"]

# Latencia: buckets en segundos pensados para un CRUD sobre MongoDB.
LATENCY_BUCKETS = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)

# Tamaño de respuesta: buckets en bytes (de un 404 corto a un listado grande).
RESPONSE_SIZE_BUCKETS = (
    64, 128, 256, 512, 1_024, 2_048, 4_096, 8_192, 16_384, 65_536, 262_144, 1_048_576,
)


def response_size_histogram(
    metric_name: str = "http_response_size_bytes",
    buckets=RESPONSE_SIZE_BUCKETS,
    registry=REGISTRY,
) -> Callable[[Info], None]:
    """Histograma del tamaño de las respuestas (bytes) por método y ruta."""
    histogram = Histogram(
        metric_name,
        "Tamaño de las respuestas HTTP en bytes.",
        labelnames=("handler", "method"),
        buckets=buckets,
        registry=registry,
    )

    def instrumentation(info: Info) -> None:
        if info.response is None:
            return
        size = info.response.headers.get("Content-Length")
        if size is None and hasattr(info.response, "body"):
            size = len(info.response.body)
        if size is None:
            return
        histogram.labels(info.modified_handler, info.method).observe(int(size))

    return instrumentation


def setup_metrics(app) -> Instrumentator:
    """Registra las métricas en la app y expone el endpoint /metrics."""
    instrumentator = Instrumentator(
        should_group_status_codes=False,       # 200, 201, 404... en vez de 2xx/4xx
        should_ignore_untemplated=True,        # rutas inexistentes no crean series
        excluded_handlers=EXCLUDED_HANDLERS,
        should_instrument_requests_inprogress=True,
        inprogress_name="http_requests_inprogress",
        inprogress_labels=True,                # requests en curso por método y ruta
    )

    # Total de requests y requests por status code.
    instrumentator.add(metrics.requests())
    # Latencia (histograma en segundos) por método y ruta.
    instrumentator.add(
        metrics.latency(should_include_status=False, buckets=LATENCY_BUCKETS)
    )
    # Tamaño de las respuestas (histograma en bytes) por método y ruta.
    instrumentator.add(response_size_histogram())

    instrumentator.instrument(app).expose(
        app, endpoint="/metrics", include_in_schema=False
    )
    return instrumentator
