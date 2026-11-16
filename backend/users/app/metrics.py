from prometheus_client import Counter, Histogram

requests_total = Counter(
    "users_http_requests_total",
    "Total de solicitudes HTTP",
    ["method", "route", "status_code"]
)

request_duration = Histogram(
    "users_http_request_duration_seconds",
    "Duración de las solicitudes HTTP en segundos",
    ["method", "route"],
    buckets=(
        0.005,
        0.01,
        0.025,
        0.05,
        0.1,
        0.25,
        0.5,
        1.0,
        2.5,
        5.0,
        10.0
    )
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
    method = info.method
    status_code = str(info.modified_status)

    requests_total.labels(
        method=method,
        route=route,
        status_code=status_code
    ).inc()

    request_duration.labels(
        method=method,
        route=route
    ).observe(info.modified_duration)


    if info.response is not None and info.response.body is not None:
        response_size.labels(
            method=method,
            route=route
        ).observe(len(info.response.body))