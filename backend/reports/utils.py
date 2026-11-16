"""Funciones auxiliares para convertir documentos y validar IDs de Mongo."""
from bson import ObjectId
from bson.errors import InvalidId
from fastapi import HTTPException, status


def to_out(doc: dict) -> dict:
    """Convierte el _id de Mongo en un campo `id` de tipo str."""
    doc["id"] = str(doc.pop("_id"))
    return doc


def parse_id(reporte_id: str) -> ObjectId:
    """Valida el formato del ID; responde 422 si es inválido."""
    try:
        return ObjectId(reporte_id)
    except (InvalidId, TypeError):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="ID con formato inválido",
        )