import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import FastAPI, HTTPException, Query, Request, Response, status
from fastapi.exception_handlers import (
    http_exception_handler,
    request_validation_exception_handler,
)
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from pymongo.errors import DuplicateKeyError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.db import COLLECTION_NAME, connect_to_mongo, close_mongo, get_database
from app.eventos import construir_notificaciones, tipos_a_cancelar
from app.models import (
    DespachoResponse,
    EventoPrestamo,
    EventoPrestamoResponse,
    NotificacionCreate,
    NotificacionListResponse,
    NotificacionResponse,
    NotificacionUpdate,
)
from app.observability import ObservabilityMiddleware, configure_logging


configure_logging()
logger = logging.getLogger("notificaciones")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_to_mongo()
    logger.info("Conexión con MongoDB establecida")
    yield
    await close_mongo()
    logger.info("Conexión con MongoDB cerrada")


app = FastAPI(
    title="API de Notificaciones",
    description=(
        "API REST para gestionar recordatorios de devolución, "
        "alertas de vencimiento y confirmaciones relacionadas "
        "con préstamos."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

# Orígenes permitidos para el UI de React, separados por comas.
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mide (Prometheus) y loggea (JSON) cada petición, excepto /health y /metrics.
app.add_middleware(ObservabilityMiddleware)


@app.exception_handler(RequestValidationError)
async def log_validation_error(request: Request, exc: RequestValidationError):
    logger.warning(
        "Validación fallida",
        extra={
            "status_code": 422,
            "errores": [
                {
                    "campo": ".".join(str(p) for p in error.get("loc", [])),
                    "mensaje": error.get("msg"),
                }
                for error in exc.errors()
            ],
        },
    )
    return await request_validation_exception_handler(request, exc)


@app.exception_handler(StarletteHTTPException)
async def log_http_error(request: Request, exc: StarletteHTTPException):
    if exc.status_code == status.HTTP_404_NOT_FOUND:
        message = "Recurso no encontrado"
    elif exc.status_code == status.HTTP_409_CONFLICT:
        message = "Conflicto con un recurso existente"
    else:
        message = "Petición rechazada"

    logger.log(
        logging.ERROR if exc.status_code >= 500 else logging.WARNING,
        message,
        extra={
            "status_code": exc.status_code,
            "detail": exc.detail,
            **request.path_params,
        },
    )
    return await http_exception_handler(request, exc)


def parse_object_id(notification_id: str) -> ObjectId:
    try:
        return ObjectId(notification_id)
    except (InvalidId, TypeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El ID proporcionado no es un ObjectId válido.",
        )


def serialize_notification(document: dict) -> NotificacionResponse:
    document_data = {
        key: value
        for key, value in document.items()
        if key != "_id"
    }

    return NotificacionResponse(
        id=str(document["_id"]),
        **document_data,
    )


@app.get("/metrics", include_in_schema=False)
async def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get(
    "/health",
    summary="Comprobar estado de la API y MongoDB",
)
async def health():
    try:
        database = get_database()
        await database.command("ping")

        return {
            "status": "ok",
            "database": "ok",
        }

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"MongoDB no disponible: {exc}",
        )


@app.post(
    "/notificaciones",
    response_model=NotificacionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear una notificación",
)
async def create_notification(
    notification: NotificacionCreate,
):
    database = get_database()
    collection = database[COLLECTION_NAME]

    now = datetime.now(timezone.utc)

    document = notification.model_dump()
    document["created_at"] = now
    document["updated_at"] = None

    try:
        result = await collection.insert_one(document)

    except DuplicateKeyError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Ya existe una notificación con el código "
                f"'{notification.codigo}'."
            ),
        )

    created = await collection.find_one(
        {"_id": result.inserted_id}
    )

    logger.info(
        "Notificación creada",
        extra={
            "notification_id": str(result.inserted_id),
            "codigo": notification.codigo,
            "tipo": notification.tipo,
        },
    )

    return serialize_notification(created)


@app.get(
    "/notificaciones",
    response_model=NotificacionListResponse,
    summary="Obtener notificaciones",
)
async def list_notifications(
    skip: int = Query(
        default=0,
        ge=0,
    ),
    limit: int = Query(
        default=20,
        ge=1,
        le=100,
    ),
    tipo: str | None = Query(
        default=None,
    ),
    estado: str | None = Query(
        default=None,
    ),
    destinatario_id: str | None = Query(
        default=None,
    ),
    prestamo_id: str | None = Query(
        default=None,
    ),
):
    database = get_database()
    collection = database[COLLECTION_NAME]

    query = {}

    if tipo:
        query["tipo"] = tipo

    if estado:
        query["estado"] = estado

    if destinatario_id:
        query["destinatario_id"] = destinatario_id

    if prestamo_id:
        query["prestamo_id"] = prestamo_id

    total = await collection.count_documents(query)

    cursor = (
        collection
        .find(query)
        .sort("created_at", -1)
        .skip(skip)
        .limit(limit)
    )

    documents = await cursor.to_list(length=limit)

    items = [
        serialize_notification(document)
        for document in documents
    ]

    logger.info(
        "Notificaciones listadas",
        extra={"filtros": query, "total": total, "devueltas": len(items)},
    )

    return NotificacionListResponse(
        items=items,
        total=total,
        skip=skip,
        limit=limit,
    )


@app.post(
    "/notificaciones/despachar",
    response_model=DespachoResponse,
    summary="Enviar las notificaciones programadas que ya vencieron",
)
async def dispatch_notifications():
    database = get_database()
    collection = database[COLLECTION_NAME]

    now = datetime.now(timezone.utc)

    # Todavía no hay proveedor real de email/push: "enviar" equivale
    # a marcar la notificación como enviada.
    result = await collection.update_many(
        {
            "estado": "pendiente",
            "fecha_programada": {"$lte": now},
        },
        {"$set": {"estado": "enviada", "updated_at": now}},
    )

    logger.info(
        "Notificaciones despachadas",
        extra={"despachadas": result.modified_count},
    )

    return DespachoResponse(despachadas=result.modified_count)


@app.get(
    "/notificaciones/{notification_id}",
    response_model=NotificacionResponse,
    summary="Obtener una notificación por ID",
)
async def get_notification(
    notification_id: str,
):
    database = get_database()
    collection = database[COLLECTION_NAME]

    object_id = parse_object_id(notification_id)

    document = await collection.find_one(
        {"_id": object_id}
    )

    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notificación no encontrada.",
        )

    logger.info(
        "Notificación consultada",
        extra={"notification_id": notification_id},
    )

    return serialize_notification(document)


@app.put(
    "/notificaciones/{notification_id}",
    response_model=NotificacionResponse,
    summary="Actualizar una notificación",
)
async def update_notification(
    notification_id: str,
    notification: NotificacionUpdate,
):
    database = get_database()
    collection = database[COLLECTION_NAME]

    object_id = parse_object_id(notification_id)

    updates = notification.model_dump(
        exclude_unset=True,
    )

    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se proporcionaron campos para actualizar.",
        )

    if (
        updates.get("estado") == "leida"
        and "leida_at" not in updates
    ):
        updates["leida_at"] = datetime.now(timezone.utc)

    updates["updated_at"] = datetime.now(timezone.utc)

    try:
        result = await collection.update_one(
            {"_id": object_id},
            {"$set": updates},
        )

    except DuplicateKeyError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe otra notificación con ese código.",
        )

    if result.matched_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notificación no encontrada.",
        )

    document = await collection.find_one(
        {"_id": object_id}
    )

    logger.info(
        "Notificación actualizada",
        extra={
            "notification_id": notification_id,
            "campos": sorted(k for k in updates if k != "updated_at"),
        },
    )

    return serialize_notification(document)


@app.patch(
    "/notificaciones/{notification_id}/leida",
    response_model=NotificacionResponse,
    summary="Marcar una notificación como leída",
)
async def mark_notification_read(
    notification_id: str,
):
    database = get_database()
    collection = database[COLLECTION_NAME]

    object_id = parse_object_id(notification_id)

    now = datetime.now(timezone.utc)

    result = await collection.update_one(
        {"_id": object_id},
        {"$set": {"estado": "leida", "leida_at": now, "updated_at": now}},
    )

    if result.matched_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notificación no encontrada.",
        )

    document = await collection.find_one(
        {"_id": object_id}
    )

    logger.info(
        "Notificación marcada como leída",
        extra={"notification_id": notification_id},
    )

    return serialize_notification(document)


@app.delete(
    "/notificaciones/{notification_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar una notificación",
)
async def delete_notification(
    notification_id: str,
):
    database = get_database()
    collection = database[COLLECTION_NAME]

    object_id = parse_object_id(notification_id)

    result = await collection.delete_one(
        {"_id": object_id}
    )

    if result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notificación no encontrada.",
        )

    logger.info(
        "Notificación eliminada",
        extra={"notification_id": notification_id},
    )

    return None


@app.post(
    "/eventos/prestamos",
    response_model=EventoPrestamoResponse,
    summary="Reaccionar a un evento del módulo de Préstamos",
)
async def handle_loan_event(
    evento: EventoPrestamo,
):
    database = get_database()
    collection = database[COLLECTION_NAME]

    now = datetime.now(timezone.utc)

    canceladas = 0
    tipos = tipos_a_cancelar(evento)

    if tipos:
        result = await collection.update_many(
            {
                "prestamo_id": evento.prestamo_id,
                "tipo": {"$in": tipos},
                "estado": "pendiente",
            },
            {"$set": {"estado": "cancelada", "updated_at": now}},
        )
        canceladas = result.modified_count

    notificaciones = []

    for notification in construir_notificaciones(evento, now):
        document = notification.model_dump()
        document["created_at"] = now
        document["updated_at"] = None

        # $setOnInsert hace el evento idempotente: si Préstamos
        # reintenta, se devuelve la notificación ya existente.
        await collection.update_one(
            {"codigo": notification.codigo},
            {"$setOnInsert": document},
            upsert=True,
        )

        stored = await collection.find_one(
            {"codigo": notification.codigo}
        )
        notificaciones.append(serialize_notification(stored))

    logger.info(
        "Evento de préstamo procesado",
        extra={
            "evento": evento.evento,
            "prestamo_id": evento.prestamo_id,
            "notificaciones_generadas": [n.id for n in notificaciones],
            "canceladas": canceladas,
        },
    )

    return EventoPrestamoResponse(
        evento=evento.evento,
        prestamo_id=evento.prestamo_id,
        notificaciones=notificaciones,
        canceladas=canceladas,
    )
