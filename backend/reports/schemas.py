"""Modelos Pydantic para validar entradas y salidas de la API."""
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

TipoReporte = Literal["uso_activos", "prestamos", "inventario", "mantenimiento"]


class ReporteBase(BaseModel):
    titulo: str = Field(..., min_length=3, max_length=120)
    tipo: TipoReporte
    descripcion: Optional[str] = Field(None, max_length=500)
    periodo_inicio: datetime
    periodo_fin: datetime
    generado_por: str = Field(..., min_length=2)
    metricas: dict[str, float] = Field(default_factory=dict)


class ReporteCreate(ReporteBase):
    pass


class ReporteUpdate(BaseModel):
    titulo: Optional[str] = Field(None, min_length=3, max_length=120)
    tipo: Optional[TipoReporte] = None
    descripcion: Optional[str] = Field(None, max_length=500)
    periodo_inicio: Optional[datetime] = None
    periodo_fin: Optional[datetime] = None
    generado_por: Optional[str] = Field(None, min_length=2)
    metricas: Optional[dict[str, float]] = None


class ReporteOut(ReporteBase):
    id: str
    creado_en: datetime