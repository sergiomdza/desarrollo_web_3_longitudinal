from typing import Any, Optional, Union

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import FastAPI, HTTPException, Query, Response, status
from pymongo import ReturnDocument

import database
from models import Activo, ActivoCreate, EstadoActivo

app = FastAPI(
    title="Categorías & Ubicaciones",
    description="Catálogo de activos: tipos de activos, ubicaciones físicas y disponibilidad por ubicación (Equipo 2).",
    version="0.1.0",
)


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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Activo no encontrado")
    return _to_activo(document)


@app.put("/activos/{activo_id}", response_model=Activo)
def update_activo(activo_id: str, activo: ActivoCreate):
    document = database.activos.find_one_and_update(
        {"_id": _parse_object_id(activo_id)},
        {"$set": activo.model_dump(exclude_none=True)},
        return_document=ReturnDocument.AFTER,
    )
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Activo no encontrado")
    return _to_activo(document)


@app.delete("/activos/{activo_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_activo(activo_id: str):
    result = database.activos.delete_one({"_id": _parse_object_id(activo_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Activo no encontrado")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
