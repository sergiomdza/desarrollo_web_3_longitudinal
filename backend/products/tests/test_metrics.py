import asyncio

from fastapi import FastAPI
from prometheus_client import REGISTRY

from metrics import instrumentar

# App mínima (sin Mongo) con una ruta con parámetro, como /activos/{activo_id}.
app = FastAPI()
instrumentar(app)


@app.get("/cosas/{cosa_id}")
def get_cosa(cosa_id: int):
    return {"id": cosa_id}


class _Respuesta:
    def __init__(self, status_code, content):
        self.status_code = status_code
        self.content = content
        self.text = content.decode()


class _Cliente:
    """Cliente GET mínimo que llama a la app ASGI directo (sin httpx)."""

    def get(self, path):
        return asyncio.run(self._get(path))

    async def _get(self, path):
        scope = {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": "GET",
            "scheme": "http",
            "path": path,
            "raw_path": path.encode(),
            "root_path": "",
            "query_string": b"",
            "headers": [(b"host", b"test")],
            "client": ("test", 1),
            "server": ("test", 80),
        }
        mensajes = []

        async def receive():
            return {"type": "http.request", "body": b"", "more_body": False}

        async def send(message):
            mensajes.append(message)

        await app(scope, receive, send)
        status_code = next(m["status"] for m in mensajes if m["type"] == "http.response.start")
        body = b"".join(m.get("body", b"") for m in mensajes if m["type"] == "http.response.body")
        return _Respuesta(status_code, body)


client = _Cliente()


def _valor(nombre, **labels):
    return REGISTRY.get_sample_value(nombre, labels) or 0.0


def test_usa_la_ruta_plantilla_y_no_el_id():
    antes = _valor("http_requests_total", method="GET", path="/cosas/{cosa_id}")

    client.get("/cosas/1")
    client.get("/cosas/2")

    assert _valor("http_requests_total", method="GET", path="/cosas/{cosa_id}") == antes + 2
    assert _valor("http_requests_total", method="GET", path="/cosas/1") == 0


def test_separa_por_status_code():
    ok_antes = _valor("http_responses_total", path="/cosas/{cosa_id}", status_code="200")
    invalido_antes = _valor("http_responses_total", path="/cosas/{cosa_id}", status_code="422")

    client.get("/cosas/7")
    client.get("/cosas/no-es-numero")

    assert _valor("http_responses_total", path="/cosas/{cosa_id}", status_code="200") == ok_antes + 1
    assert _valor("http_responses_total", path="/cosas/{cosa_id}", status_code="422") == invalido_antes + 1


def test_rutas_inexistentes_son_sin_ruta():
    antes = _valor("http_responses_total", path="sin_ruta", status_code="404")

    client.get("/no-existe/123")

    assert _valor("http_responses_total", path="sin_ruta", status_code="404") == antes + 1


def test_mide_duracion_y_tamano():
    respuesta = client.get("/cosas/5")
    labels = {"method": "GET", "path": "/cosas/{cosa_id}"}

    assert _valor("http_request_duration_seconds_count", **labels) > 0
    assert _valor("http_response_size_bytes_sum", **labels) >= len(respuesta.content)


def test_endpoint_metrics_expone_las_4_metricas():
    client.get("/cosas/1")
    texto = client.get("/metrics").text

    for nombre in (
        "http_requests_total",
        "http_responses_total",
        "http_request_duration_seconds_bucket",
        "http_response_size_bytes_bucket",
    ):
        assert nombre in texto
