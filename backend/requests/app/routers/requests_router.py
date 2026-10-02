from fastapi import APIRouter, HTTPException, status
from pydantic import ValidationError
from pymongo.errors import PyMongoError
from ..models.request import Requests
from ..database import requests_collection

router = APIRouter()

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
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="no se puedo conectar con la base de datos",
        )

    try:
        return [Requests(**document) for document in documents]
    except ValidationError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="imcumplimiento con el modelo pydantic",
        )

@router.get("/requests/{id}",
    response_model=Requests,
    status_code=status.HTTP_200_OK,
    responses={
        500: {"error": "imcumplimiento con el modelo pydantic"},
        503: {"error": "no hay conexion con al base de datos"},
    })
def get_request_by_id(id: str):
    try:
        document = requests_collection.find_one({"_id": id})
    except PyMongoError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="no se puedo conectar con la base de datos",
        )

    try:
        return document
    except ValidationError:
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
        {"_id": id},
        {"$set": update_dict},
        return_document=True 
        )
  except PyMongoError:
    raise HTTPException(
      status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
      detail="No se pudo conectar con la base de datos",
      )

  if result is None:
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="No se encontró"
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
        result = requests_collection.delete_one({"_id": id})
    except PyMongoError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No se pudo conectar con la base de datos",
        )

    if result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El request con ese ID no existe",
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
        created_document = requests_collection.find_one({"_id": result.inserted_id})
        
    except PyMongoError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No se pudo conectar con la base de datos o insertar el registro",
        )

    try:
        return Requests(**created_document)
    except ValidationError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="El documento guardado no cumple con el modelo Pydantic",
        )
