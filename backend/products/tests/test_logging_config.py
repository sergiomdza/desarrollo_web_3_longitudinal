import json
import logging
import sys

from logging_config import SERVICE_NAME, JsonFormatter


def _formatear(mensaje, nivel=logging.INFO, exc_info=None, **extra):
    """Crea un registro de log y regresa el JSON que escribiría el formatter."""
    registro = logging.LogRecord(
        name="categorias_ubicaciones",
        level=nivel,
        pathname=__file__,
        lineno=1,
        msg=mensaje,
        args=None,
        exc_info=exc_info,
    )
    registro.__dict__.update(extra)

    linea = JsonFormatter().format(registro)
    return linea, json.loads(linea)


def test_log_es_una_sola_linea_json_con_los_campos_minimos():
    linea, evento = _formatear("Activo creado")

    assert "\n" not in linea
    assert evento["message"] == "Activo creado"
    assert evento["level"] == "INFO"
    assert evento["service"] == SERVICE_NAME
    assert evento["timestamp"].endswith("+00:00")


def test_log_incluye_el_contexto_pasado_en_extra():
    _, evento = _formatear("Activo creado", activo_id="abc123", status_code=201)

    assert evento["activo_id"] == "abc123"
    assert evento["status_code"] == 201


def test_log_descarta_el_mensaje_con_colores_de_uvicorn():
    _, evento = _formatear("Started server process", color_message="\x1b[36mStarted\x1b[0m")

    assert "color_message" not in evento


def test_log_de_error_lleva_la_causa_en_el_mismo_registro():
    try:
        raise ValueError("algo falló")
    except ValueError:
        linea, evento = _formatear("Error inesperado", nivel=logging.ERROR, exc_info=sys.exc_info())

    assert "\n" not in linea
    assert evento["level"] == "ERROR"
    assert "ValueError: algo falló" in evento["exception"]


def test_log_no_muestra_la_uri_de_mongo():
    linea, evento = _formatear("No conecta a mongodb://admin:web3@mongo-service:27017/?authSource=admin")

    assert "web3" not in linea
    assert evento["message"] == "No conecta a mongodb://***"


def _registro():
    return logging.LogRecord("categorias_ubicaciones", logging.INFO, __file__, 1, "Activo creado", None, None)


class _Ruta:
    path = "/activos/{activo_id}"


def test_log_dentro_de_una_request_lleva_method_path_y_duracion():
    from logging_config import ContextoRequestFilter, _request_actual

    scope = {"method": "DELETE", "path": "/activos/abc123", "route": _Ruta()}
    token = _request_actual.set({"scope": scope, "inicio": 0.0})
    try:
        registro = _registro()
        ContextoRequestFilter().filter(registro)
    finally:
        _request_actual.reset(token)

    assert registro.method == "DELETE"
    assert registro.path == "/activos/{activo_id}"  # plantilla, no el ID real
    assert registro.duration_ms >= 0


def test_log_fuera_de_una_request_no_lleva_contexto_http():
    from logging_config import ContextoRequestFilter

    registro = _registro()
    ContextoRequestFilter().filter(registro)

    assert not hasattr(registro, "method")
    assert not hasattr(registro, "path")
