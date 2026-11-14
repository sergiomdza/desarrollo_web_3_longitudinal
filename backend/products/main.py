import logging
import re
from typing import Any, NoReturn, Optional, Union

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import FastAPI, HTTPException, Query, Request, Response, status
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pymongo import ReturnDocument
from pymongo.errors import ConnectionFailure, PyMongoError

import database
from models import Activo, ActivoCreate, EstadoActivo

# Logger de los eventos de dominio del módulo. El formato JSON, el campo
# "service" y el contexto de la request (method, path, duration_ms) los agrega
# la configuración de logging del servicio; aquí solo decimos QUÉ pasó.
logger = logging.getLogger("categorias_ubicaciones")

app = FastAPI(
    title="Categorías & Ubicaciones",
    description="Catálogo de activos: tipos de activos, ubicaciones físicas y disponibilidad por ubicación (Equipo 2).",
    version="0.1.0",
)


# --- Situaciones anómalas -----------------------------------------------------


@app.exception_handler(RequestValidationError)
async def log_validation_error(request: Request, exc: RequestValidationError):
    """422: registra qué campos fallaron y por qué, sin los valores enviados."""
    errores = [
        {"campo": ".".join(str(parte) for parte in error["loc"]), "motivo": error["msg"]}
        for error in exc.errors()
    ]
    logger.warning(
        "Validación fallida",
        extra={"operacion": _operacion(request), "status_code": 422, "errores": errores},
    )
    return await request_validation_exception_handler(request, exc)


@app.exception_handler(PyMongoError)
async def log_mongo_error(request: Request, exc: PyMongoError):
    """Errores de MongoDB: la causa va dentro del mismo registro JSON, sin traceback."""
    # Mongo caído o inalcanzable -> 503; Mongo respondió con un error -> 500
    status_code = 503 if isinstance(exc, ConnectionFailure) else 500
    logger.error(
        "Error de MongoDB",
        extra={
            "operacion": _operacion(request),
            "status_code": status_code,
            "error_type": type(exc).__name__,
            "mongo_code": getattr(exc, "code", None),
            "error_detail": _detalle_seguro(exc),
        },
    )
    detail = (
        "La base de datos no está disponible"
        if status_code == 503
        else "Error interno al consultar la base de datos"
    )
    return JSONResponse(status_code=status_code, content={"detail": detail})


def _operacion(request: Request) -> Optional[str]:
    """Nombre del endpoint que atendía la request (p. ej. "create_activo")."""
    endpoint = request.scope.get("endpoint")
    return getattr(endpoint, "__name__", None)


def _detalle_seguro(exc: PyMongoError) -> str:
    """Mensaje del error sin la topología del cluster ni cadenas de conexión."""
    detalle = str(exc).split(", Topology Description")[0]
    detalle = re.sub(r"mongodb(\+srv)?://\S+", "mongodb://***", detalle)
    return detalle[:300]


def _activo_no_encontrado(activo_id: str, operacion: str) -> NoReturn:
    logger.warning(
        "Activo no encontrado",
        extra={"activo_id": activo_id, "operacion": operacion, "status_code": 404},
    )
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Activo no encontrado")


def _parse_object_id(value: str) -> Union[ObjectId, str]:
    try:
        return ObjectId(value)
    except InvalidId:
        return value


def _to_activo(payload: Optional[dict[str, Any]]) -> Optional[Activo]:
    if payload is None:
        return None

    item = dict(payload)
    item["id"] = str(item.pop("_id"))
    return Activo.model_validate(item)


@app.get("/")
def default():
    return {"message": "Servicio de Categorías & Ubicaciones - Equipo 2"}


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "database": "ok" if database.ping() else "unreachable",
    }


@app.post("/activos", response_model=Activo, status_code=status.HTTP_201_CREATED)
def create_activo(activo: ActivoCreate):
    created_id = database.activos.insert_one(activo.model_dump(exclude_none=True)).inserted_id
    logger.info(
        "Activo creado",
        extra={"activo_id": str(created_id), "codigo": activo.codigo, "status_code": 201},
    )
    document = database.activos.find_one({"_id": created_id})
    return _to_activo(document)


@app.get("/activos", response_model=list[Activo])
def list_activos(
    estado: Optional[EstadoActivo] = Query(default=None),
    categoria: Optional[str] = Query(default=None),
    ubicacion: Optional[str] = Query(default=None),
    codigo: Optional[str] = Query(default=None),
    nombre: Optional[str] = Query(default=None),
):
    filters: dict[str, Any] = {}

    if estado is not None:
        filters["estado"] = estado.value
    if categoria:
        filters["categoria.nombre"] = {"$regex": categoria, "$options": "i"}
    if ubicacion:
        filters["ubicacion.nombre"] = {"$regex": ubicacion, "$options": "i"}
    if codigo:
        filters["codigo"] = {"$regex": codigo, "$options": "i"}
    if nombre:
        filters["nombre"] = {"$regex": nombre, "$options": "i"}

    documents = database.activos.find(filters)
    return [_to_activo(doc) for doc in documents]


@app.get("/activos/{activo_id}", response_model=Activo)
def get_activo(activo_id: str):
    document = database.activos.find_one({"_id": _parse_object_id(activo_id)})
    if document is None:
        _activo_no_encontrado(activo_id, "get_activo")
    return _to_activo(document)


@app.put("/activos/{activo_id}", response_model=Activo)
def update_activo(activo_id: str, activo: ActivoCreate):
    document = database.activos.find_one_and_update(
        {"_id": _parse_object_id(activo_id)},
        {"$set": activo.model_dump(exclude_none=True)},
        return_document=ReturnDocument.AFTER,
    )
    if document is None:
        _activo_no_encontrado(activo_id, "update_activo")
    logger.info(
        "Activo actualizado",
        extra={
            "activo_id": activo_id,
            "codigo": activo.codigo,
            "estado": activo.estado.value,
            "status_code": 200,
        },
    )
    return _to_activo(document)


@app.delete("/activos/{activo_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_activo(activo_id: str):
    result = database.activos.delete_one({"_id": _parse_object_id(activo_id)})
    if result.deleted_count == 0:
        _activo_no_encontrado(activo_id, "delete_activo")
    logger.info("Activo eliminado", extra={"activo_id": activo_id, "status_code": 204})
    return Response(status_code=status.HTTP_204_NO_CONTENT)
