import logging

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import HTTPException, status

logger = logging.getLogger("reportes.utils")


def to_out(doc: dict) -> dict:
    """Convierte el _id de Mongo en un campo `id` de tipo str."""
    doc["id"] = str(doc.pop("_id"))
    return doc


def parse_id(reporte_id: str) -> ObjectId:
    """Valida el formato del ID; responde 422 si es inválido."""
    try:
        return ObjectId(reporte_id)
    except (InvalidId, TypeError):
        logger.warning(
            "ID de reporte con formato inválido",
            extra={"reporte_id": reporte_id[:64], "status_code": 422},
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="ID con formato inválido",
        )