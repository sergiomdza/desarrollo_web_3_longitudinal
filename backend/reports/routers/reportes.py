"""Endpoints CRUD de la entidad `reporte`."""
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query, Response, status
from pymongo import ReturnDocument

from database import reportes
from schemas import ReporteCreate, ReporteOut, ReporteUpdate
from utils import parse_id, to_out

router = APIRouter(prefix="/reportes", tags=["reportes"])


@router.post("", response_model=ReporteOut, status_code=status.HTTP_201_CREATED)
def crear_reporte(reporte: ReporteCreate):
    doc = reporte.model_dump()
    doc["creado_en"] = datetime.now(timezone.utc)
    result = reportes.insert_one(doc)
    doc["_id"] = result.inserted_id
    return to_out(doc)


@router.get("", response_model=list[ReporteOut])
def listar_reportes(skip: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200)):
    return [to_out(d) for d in reportes.find().skip(skip).limit(limit)]


@router.get("/{reporte_id}", response_model=ReporteOut)
def obtener_reporte(reporte_id: str):
    doc = reportes.find_one({"_id": parse_id(reporte_id)})
    if doc is None:
        raise HTTPException(status_code=404, detail="Reporte no encontrado")
    return to_out(doc)


@router.put("/{reporte_id}", response_model=ReporteOut)
def actualizar_reporte(reporte_id: str, cambios: ReporteUpdate):
    oid = parse_id(reporte_id)
    data = cambios.model_dump(exclude_unset=True)
    if not data:
        doc = reportes.find_one({"_id": oid})
    else:
        doc = reportes.find_one_and_update(
            {"_id": oid}, {"$set": data}, return_document=ReturnDocument.AFTER
        )
    if doc is None:
        raise HTTPException(status_code=404, detail="Reporte no encontrado")
    return to_out(doc)


@router.delete("/{reporte_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_reporte(reporte_id: str):
    result = reportes.delete_one({"_id": parse_id(reporte_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Reporte no encontrado")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
