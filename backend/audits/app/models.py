from datetime import datetime
from pydantic import BaseModel, Field


class Auditoria(BaseModel):
    id: int = Field(..., gt=0)
    nombre: str = Field(..., min_length=1)
    usuario: str = Field(..., min_length=1)
    fecha: datetime

class AuditoriaUpdate(BaseModel):
    nombre: str | None = Field(default=None, min_length=1)
    usuario: str | None = Field(default=None, min_length=1)
    fecha: datetime | None = None