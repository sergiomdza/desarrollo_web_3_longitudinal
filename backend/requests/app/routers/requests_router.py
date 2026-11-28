import logging

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, HTTPException, status
from pydantic import ValidationError
from pymongo.errors import PyMongoError
from ..models.request import Requests
from ..database import requests_collection

router = APIRouter()

logger = logging.getLogger("requests-backend")


def to_object_id(id: str) -> ObjectId:
    """Convierte el ID recibido en un ObjectId de MongoDB."""
    try:
        return ObjectId(id)
    except InvalidId:
        logger.warning(
            "Se intento consultar una solicitud con un ID invalido",
            extra={
                "event": "request_not_found",
                "request_id": id,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No existe una solicitud con ese ID",
        )


@router.get(
    "/requests",
    response_model=list[Requests],
    status_code=status.HTTP_200_OK,
    responses={
        500: {"error": "imcumplimiento con el modelo pydantic"},
        503: {"error": "no hay conexion con al base de datos"},
    },
)
def get_requests():
    try:
        documents = list(requests_collection.find({}, {"_id": 0}))
    except PyMongoError:
        logger.exception(
            "Error al consultar las solicitudes en MongoDB",
            extra={
                "event": "mongodb_error",
                "operation": "get_requests",
            },
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="no se puedo conectar con la base de datos",
        )

    try:
        return [Requests(**document) for document in documents]
    except ValidationError:
        logger.exception(
            "Los datos obtenidos de MongoDB no cumplen con el modelo",
            extra={
                "event": "data_validation_error",
                "operation": "get_requests",
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="imcumplimiento con el modelo pydantic",
        )


@router.get(
    "/requests/{id}",
    response_model=Requests,
    status_code=status.HTTP_200_OK,
    responses={
        404: {"error": "No existe una solicitud con ese ID"},
        500: {"error": "imcumplimiento con el modelo pydantic"},
        503: {"error": "no hay conexion con la base de datos"},
    },
)
def get_request_by_id(id: str):
    try:
        document = requests_collection.find_one({"_id": to_object_id(id)})
    except PyMongoError:
        logger.exception(
            "Error al consultar una solicitud en MongoDB",
            extra={
                "event": "mongodb_error",
                "operation": "get_request_by_id",
                "request_id": id,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="no se puedo conectar con la base de datos",
        )

    if document is None:
        logger.warning(
            "No se encontro la solicitud solicitada",
            extra={
                "event": "request_not_found",
                "request_id": id,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No existe una solicitud con ese ID",
        )

    try:
        return Requests(**document)
    except ValidationError:
        logger.exception(
            "La solicitud obtenida no cumple con el modelo",
            extra={
                "event": "data_validation_error",
                "operation": "get_request_by_id",
                "request_id": id,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="imcumplimiento con el modelo pydantic",
        )


@router.put(
    "/requests/{id}",
    response_model=Requests,
    status_code=status.HTTP_200_OK,
    responses={
        500: {"error": "Datos de actualizacion invalidos"},
        404: {"error": "No se encontró el registro."},
    },
)
def update_request(id: str, updated_data: Requests):
    try:
        update_dict = updated_data.model_dump(exclude={"id"})
        result = requests_collection.find_one_and_update(
            {"_id": to_object_id(id)},
            {"$set": update_dict},
            return_document=True,
        )
    except PyMongoError:
        logger.exception(
            "Error al actualizar una solicitud en MongoDB",
            extra={
                "event": "mongodb_error",
                "operation": "update_request",
                "request_id": id,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se pudo conectar con la base de datos",
        )

    if result is None:
        logger.warning(
            "No se encontro la solicitud que se intento actualizar",
            extra={
                "event": "request_not_found",
                "request_id": id,
                "operation": "update_request",
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se encontró",
        )

    logger.info(
        "Solicitud actualizada correctamente",
        extra={
            "event": "request_updated",
            "request_id": id,
        },
    )

    return Requests(**result)


@router.delete(
    "/requests/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        404: {"description": "Request no encontrado"},
        503: {"description": "No hay conexion con la base de datos"},
    },
)
def delete_request(id: str):
    try:
        result = requests_collection.delete_one({"_id": to_object_id(id)})
    except PyMongoError:
        logger.exception(
            "Error al eliminar una solicitud en MongoDB",
            extra={
                "event": "mongodb_error",
                "operation": "delete_request",
                "request_id": id,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No se pudo conectar con la base de datos",
        )

    if result.deleted_count == 0:
        logger.warning(
            "No se encontro la solicitud que se intento eliminar",
            extra={
                "event": "request_not_found",
                "request_id": id,
                "operation": "delete_request",
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El request con ese ID no existe",
        )

    logger.info(
        "Solicitud eliminada correctamente",
        extra={
            "event": "request_deleted",
            "request_id": id,
        },
    )

    return None


@router.post(
    "/requests",
    response_model=Requests,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"description": "Datos de solicitud inválidos"},
        503: {"description": "No hay conexión con la base de datos"},
    },
)
def create_request(new_request: Requests):
    try:
        request_dict = new_request.model_dump(by_alias=True)
        result = requests_collection.insert_one(request_dict)
        created_document = requests_collection.find_one(
            {"_id": result.inserted_id}
        )

    except PyMongoError:
        logger.exception(
            "Error al crear una solicitud en MongoDB",
            extra={
                "event": "mongodb_error",
                "operation": "create_request",
            },
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No se pudo conectar con la base de datos o insertar el registro",
        )

    try:
        created_request = Requests(**created_document)
    except ValidationError:
        logger.exception(
            "La solicitud guardada no cumple con el modelo",
            extra={
                "event": "data_validation_error",
                "operation": "create_request",
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="El documento guardado no cumple con el modelo Pydantic",
        )

    logger.info(
        "Solicitud creada correctamente",
        extra={
            "event": "request_created",
            "request_id": str(result.inserted_id),
        },
    )

    return created_request