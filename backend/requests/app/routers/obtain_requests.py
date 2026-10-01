from fastapi import APIRouter, HTTPException, status
from pydantic import ValidationError
from pymongo.errors import PyMongoError
from ..models.request import Requests
from ..database import requests_collection

router = APIRouter()

#router para obtener lista de requests
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
