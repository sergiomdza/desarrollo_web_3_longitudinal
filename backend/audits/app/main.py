# Se configura antes de cualquier otro import para que todo lo que se loggee
# (incluido Uvicorn y los errores al conectar con MongoDB) salga en JSON.
from app.logging_config import get_logger, setup_logging

setup_logging()

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from prometheus_client import Histogram
from pymongo.errors import PyMongoError
from prometheus_fastapi_instrumentator import Instrumentator, metrics

from app.models import Auditoria, AuditoriaUpdate
from app.database import auditorias_collection

logger = get_logger("app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Servicio de auditorías iniciado")
    yield
    logger.info("Servicio de auditorías detenido")


app = FastAPI(lifespan=lifespan)


# Validaciones fallidas (422): se loggea qué campos fallaron, sin los valores enviados.
@app.exception_handler(RequestValidationError)
async def validacion_fallida(request: Request, exc: RequestValidationError):
    logger.warning(
        "Validación fallida",
        extra={
            "method": request.method,
            "path": request.url.path,
            "status_code": 422,
            "errores": [
                {"campo": ".".join(str(parte) for parte in error["loc"]), "motivo": error["msg"]}
                for error in exc.errors()
            ],
        },
    )
    return await request_validation_exception_handler(request, exc)


# Errores con MongoDB: la causa va dentro del mismo registro JSON (campo "error").
@app.exception_handler(PyMongoError)
async def error_mongodb(request: Request, exc: PyMongoError):
    logger.error(
        "Error en la operación con MongoDB",
        exc_info=exc,
        extra={"method": request.method, "path": request.url.path, "status_code": 503},
    )
    return JSONResponse(status_code=503, content={"detail": "Error al comunicarse con la base de datos"})

# La librería trae el tamaño de respuesta como Summary; el proyecto lo pide como histograma.
response_size = Histogram(
    "http_response_size_bytes",
    "Tamaño de las respuestas HTTP en bytes.",
    ["handler", "method"],
    buckets=(64, 128, 256, 512, 1024, 2048, 4096, 8192, 16384, 65536, 262144, 1048576),
)

Instrumentator(
    should_group_status_codes=False,              # status exacto: 200, 201, 404, 422...
    should_ignore_untemplated=True,               # rutas inexistentes no crean series
    excluded_handlers=["^/health$", "^/metrics$"],
    should_instrument_requests_inprogress=True,   # requests en curso
    inprogress_labels=True,                       # ...por método y ruta
).add(
    metrics.requests()                            # total y por status code
).add(
    metrics.latency(should_include_status=False)  # latencia (histograma, segundos)
).add(
    lambda info: response_size.labels(info.modified_handler, info.method).observe(
        int(info.response.headers.get("Content-Length", 0))
    ) if info.response is not None else None     # tamaño de respuesta (histograma, bytes)
).instrument(app).expose(app, endpoint="/metrics")


@app.get("/")
def root():
    return {"message": "API del equipo de Auditorías funcionando"}


@app.get("/health")
def health_check():
    return {"status": "workflow funcionando correctamente"}

## Crud basico

@app.get("/auditorias", response_model=list[Auditoria])
def get_auditorias():
    return list(auditorias_collection.find({},{"_id": 0}))

@app.get("/auditorias/{id}", response_model=Auditoria)
def get_auditoria(id: int):
    
    auditoria = auditorias_collection.find_one(
        {"id": id},
        {"_id": 0}
    )

    if auditoria is None: 
        logger.warning("Auditoría no encontrada", extra={"auditoria_id": id, "method": "GET"})
        raise HTTPException(status_code=404,detail="Auditoría no encontrada")

    return auditoria

@app.post("/auditorias", response_model=Auditoria, status_code=201)
def create_auditoria(auditoria: Auditoria):

    if auditorias_collection.find_one({"id": auditoria.id}):
        logger.warning("Ya existe una auditoría con ese ID", extra={"auditoria_id": auditoria.id})
        raise HTTPException(status_code=409,detail="Ya existe una auditoría con ese ID")

    auditorias_collection.insert_one(auditoria.model_dump())
    logger.info("Auditoría creada", extra={"auditoria_id": auditoria.id, "nombre": auditoria.nombre})

    return auditoria

@app.put("/auditorias/{id}", response_model=Auditoria)
def update_auditoria(id: int, auditoria: AuditoriaUpdate):

    if auditorias_collection.find_one({"id": id}) is None:
        logger.warning("Auditoría no encontrada", extra={"auditoria_id": id, "method": "PUT"})
        raise HTTPException(status_code=404,detail="Auditoría no encontrada")

    datos = auditoria.model_dump(exclude_unset=True)

    if datos:
        auditorias_collection.update_one({"id": id},{"$set": datos})

    logger.info("Auditoría actualizada", extra={"auditoria_id": id, "campos": list(datos)})

    return auditorias_collection.find_one({"id": id},{"_id": 0})

@app.delete("/auditorias/{id}", status_code=200)
def delete_auditoria(id: int):
    
    resultado = auditorias_collection.delete_one({"id": id})

    if resultado.deleted_count == 0:
        logger.warning("Auditoría no encontrada", extra={"auditoria_id": id, "method": "DELETE"})
        raise HTTPException(status_code=404,detail="Auditoría no encontrada")

    logger.info("Auditoría eliminada", extra={"auditoria_id": id})

    return {"message": "Auditoría eliminada correctamente"}