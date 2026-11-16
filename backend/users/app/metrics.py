from prometheus_client import Counter, Histogram

requests_by_status = Counter(
    "users_http_requests_by_status_total",
    "Total de requests por ruta y código HTTP",
    ["route", "status_code"]
)

response_size = Histogram(
    "users_http_response_body_size_bytes",
    "Tamaño de las respuestas HTTP en bytes",
    ["method", "route"],
    buckets=(
        100,
        500,
        1000,
        5000,
        10000,
        50000,
        100000
    )
)

def custom_metrics(info):
    route = info.modified_handler

    requests_by_status.labels(
        route=route,
        status_code=info.modified_status
    ).inc()

    if info.response is not None:
        response_size.labels(
            method=info.method,
            route=route
        ).observe(len(info.response.body))
