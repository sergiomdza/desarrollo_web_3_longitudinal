from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


TipoNotificacion = Literal[
    "recordatorio_devolucion",
    "alerta_vencimiento",
    "confirmacion_aprobacion",
    "confirmacion_rechazo",
    "notificacion_general",
]

CanalNotificacion = Literal[
    "email",
    "whatsapp",
    "push",
    "in_app",
]

EstadoNotificacion = Literal[
    "pendiente",
    "enviada",
    "leida",
    "fallida",
    "cancelada",
]

TipoEventoPrestamo = Literal[
    "prestamo_aprobado",
    "prestamo_rechazado",
    "prestamo_por_vencer",
    "prestamo_vencido",
    "prestamo_devuelto",
]


class NotificacionBase(BaseModel):
    codigo: str = Field(
        ...,
        min_length=3,
        max_length=50,
        pattern=r"^[A-Za-z0-9_-]+$",
        description="Identificador funcional de la notificación",
    )

    tipo: TipoNotificacion

    canal: CanalNotificacion

    destinatario_id: str = Field(
        ...,
        min_length=1,
        max_length=100,
    )

    prestamo_id: str | None = Field(
        default=None,
        max_length=100,
    )

    titulo: str = Field(
        ...,
        min_length=3,
        max_length=150,
    )

    mensaje: str = Field(
        ...,
        min_length=1,
        max_length=1000,
    )

    estado: EstadoNotificacion = "pendiente"

    fecha_programada: datetime | None = None

    leida_at: datetime | None = None


class NotificacionCreate(NotificacionBase):
    pass


class NotificacionUpdate(BaseModel):
    codigo: str | None = Field(
        default=None,
        min_length=3,
        max_length=50,
        pattern=r"^[A-Za-z0-9_-]+$",
    )

    tipo: TipoNotificacion | None = None

    canal: CanalNotificacion | None = None

    destinatario_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
    )

    prestamo_id: str | None = Field(
        default=None,
        max_length=100,
    )

    titulo: str | None = Field(
        default=None,
        min_length=3,
        max_length=150,
    )

    mensaje: str | None = Field(
        default=None,
        min_length=1,
        max_length=1000,
    )

    estado: EstadoNotificacion | None = None

    fecha_programada: datetime | None = None

    leida_at: datetime | None = None


class NotificacionResponse(NotificacionBase):
    id: str
    created_at: datetime
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class NotificacionListResponse(BaseModel):
    items: list[NotificacionResponse]
    total: int
    skip: int
    limit: int


class EventoPrestamo(BaseModel):
    """Evento emitido por el módulo de Préstamos (Equipo #4)."""

    evento: TipoEventoPrestamo

    # 46 = 50 (máximo de "codigo") - 4 del prefijo "XXX-".
    prestamo_id: str = Field(
        ...,
        min_length=1,
        max_length=46,
        pattern=r"^[A-Za-z0-9_-]+$",
    )

    usuario_id: str = Field(
        ...,
        min_length=1,
        max_length=100,
    )

    activo_nombre: str | None = Field(
        default=None,
        max_length=150,
    )

    fecha_devolucion: datetime | None = None

    motivo: str | None = Field(
        default=None,
        max_length=500,
    )

    canal: CanalNotificacion = "in_app"

    @field_validator("fecha_devolucion")
    @classmethod
    def asumir_utc(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)

        return value


class EventoPrestamoResponse(BaseModel):
    evento: TipoEventoPrestamo
    prestamo_id: str
    notificaciones: list[NotificacionResponse]
    canceladas: int = 0


class DespachoResponse(BaseModel):
    despachadas: int
