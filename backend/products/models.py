from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class Categoria(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=80)
    descripcion: Optional[str] = Field(default=None, max_length=250)


class Ubicacion(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=80)
    sede: str = Field(..., min_length=1, max_length=80)
    piso: Optional[int] = Field(default=None, ge=0)


class EstadoActivo(str, Enum):
    DISPONIBLE = "disponible"
    EN_USO = "en_uso"
    MANTENIMIENTO = "mantenimiento"
    BAJA = "baja"


class ActivoBase(BaseModel):
    codigo: str = Field(..., min_length=1, max_length=50)
    nombre: str = Field(..., min_length=1, max_length=120)
    categoria: Categoria
    ubicacion: Ubicacion
    estado: EstadoActivo = EstadoActivo.DISPONIBLE
    valor_adquisicion: float = Field(..., gt=0)
    descripcion: Optional[str] = Field(default=None, max_length=500)


class ActivoCreate(ActivoBase):
    pass


class ActivoUpdate(ActivoBase):
    pass


class Activo(ActivoBase):
    id: str
