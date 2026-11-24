"""Manejadores de errores: registran el evento con su causa y devuelven la respuesta JSON."""
import logging

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pymongo.errors import ConnectionFailure, PyMongoError

logger = logging.getLogger("reportes.errors")


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def validation_handler(request: Request, exc: RequestValidationError):
        # Solo campo, mensaje y tipo: nunca el valor recibido (puede traer datos del usuario).
        errores = [
            {"campo": ".".join(str(p) for p in e["loc"]), "mensaje": e["msg"], "tipo": e["type"]}
            for e in exc.errors()
        ]
        logger.warning("Validación fallida", extra={"status_code": 422, "errores_validacion": errores})
        return JSONResponse(status_code=422, content={"detail": jsonable_encoder(exc.errors())})

    @app.exception_handler(PyMongoError)
    async def mongo_handler(request: Request, exc: PyMongoError):
        # 503 si no hay conexión con Mongo, 500 para cualquier otro fallo de la operación.
        status_code = 503 if isinstance(exc, ConnectionFailure) else 500
        logger.error("Error en la operación con MongoDB", exc_info=exc, extra={"status_code": status_code})
        detail = "Base de datos no disponible" if status_code == 503 else "Error interno"
        return JSONResponse(status_code=status_code, content={"detail": detail})