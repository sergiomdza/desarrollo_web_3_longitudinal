import json
import logging
import sys
import time
import uuid
from datetime import datetime, timezone

from fastapi import Request

logger = logging.getLogger("usuarios")

RUTAS_SIN_LOG = {"/metrics", "/usuarios/health", "/openapi.json", "/docs"}


class JsonFormatter(logging.Formatter):
    CAMPOS_EXTRA = ("metodo", "ruta", "estado", "duracion_ms", "id_peticion")

    def format(self, record):
        datos = {
            "fecha": datetime.fromtimestamp(record.created, timezone.utc).isoformat(),
            "nivel": record.levelname,
            "servicio": "usuarios",
            "logger": record.name,
            "mensaje": record.getMessage(),
        }
        for campo in self.CAMPOS_EXTRA:
            if hasattr(record, campo):
                datos[campo] = getattr(record, campo)
        if record.exc_info:
            datos["error"] = self.formatException(record.exc_info)
        return json.dumps(datos, ensure_ascii=False, default=str)


def setup_logging():
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    logging.basicConfig(level=logging.INFO, handlers=[handler], force=True)
    for nombre in ("uvicorn", "uvicorn.error"):
        logging.getLogger(nombre).handlers = []
        logging.getLogger(nombre).propagate = True
    logging.getLogger("uvicorn.access").disabled = True


async def log_requests(request: Request, call_next):
    id_peticion = request.headers.get("x-request-id") or str(uuid.uuid4())
    info = {"metodo": request.method, "ruta": request.url.path, "id_peticion": id_peticion}
    inicio = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        logger.exception("error no controlado", extra=info)
        raise
    duracion_ms = round((time.perf_counter() - inicio) * 1000, 1)
    if request.url.path not in RUTAS_SIN_LOG:
        nivel = logging.ERROR if response.status_code >= 500 else logging.INFO
        logger.log(nivel, "peticion", extra={**info, "estado": response.status_code, "duracion_ms": duracion_ms})
    response.headers["x-request-id"] = id_peticion
    return response
