"""Reglas que traducen eventos de Préstamos en notificaciones.

Las funciones de este módulo no tocan la base de datos para que puedan
probarse de forma aislada; la persistencia vive en app.main.
"""

from datetime import datetime, timedelta

from app.models import EventoPrestamo, NotificacionCreate


# Anticipación con la que se programa el recordatorio de devolución.
ANTICIPACION_RECORDATORIO = timedelta(days=1)

# Prefijos del código funcional. El código es determinista
# (prefijo + préstamo) para que reenviar el mismo evento no
# duplique notificaciones.
PREFIJOS = {
    "confirmacion_aprobacion": "APR",
    "recordatorio_devolucion": "REC",
    "confirmacion_rechazo": "RCH",
    "prestamo_por_vencer": "PVN",
    "prestamo_vencido": "VEN",
    "prestamo_devuelto": "DEV",
}

# Tipos de notificación programada que dejan de tener sentido
# cuando el préstamo termina o ya venció.
TIPOS_CANCELABLES = {
    "prestamo_vencido": ["recordatorio_devolucion"],
    "prestamo_devuelto": [
        "recordatorio_devolucion",
        "alerta_vencimiento",
    ],
}


def construir_codigo(clave: str, prestamo_id: str) -> str:
    return f"{PREFIJOS[clave]}-{prestamo_id}"


def _nombre_activo(evento: EventoPrestamo) -> str:
    if evento.activo_nombre:
        return f"el activo «{evento.activo_nombre}»"

    return "el activo solicitado"


def _del_activo(evento: EventoPrestamo) -> str:
    # "de" + "el activo ..." se contrae a "del activo ...".
    return "d" + _nombre_activo(evento)


def _formatear_fecha(fecha: datetime | None) -> str:
    if fecha is None:
        return "la fecha acordada"

    return fecha.strftime("%d/%m/%Y %H:%M")


def construir_notificaciones(
    evento: EventoPrestamo,
    now: datetime,
) -> list[NotificacionCreate]:
    activo = _nombre_activo(evento)
    del_activo = _del_activo(evento)
    fecha = _formatear_fecha(evento.fecha_devolucion)
    limite = (
        f" (fecha límite: {fecha})"
        if evento.fecha_devolucion is not None
        else ""
    )

    comunes = {
        "canal": evento.canal,
        "destinatario_id": evento.usuario_id,
        "prestamo_id": evento.prestamo_id,
    }

    if evento.evento == "prestamo_aprobado":
        notificaciones = [
            NotificacionCreate(
                **comunes,
                codigo=construir_codigo(
                    "confirmacion_aprobacion", evento.prestamo_id
                ),
                tipo="confirmacion_aprobacion",
                titulo="Préstamo aprobado",
                mensaje=(
                    f"Tu solicitud de préstamo {del_activo} fue aprobada. "
                    f"Debes devolverlo antes de {fecha}."
                ),
                estado="enviada",
            )
        ]

        if evento.fecha_devolucion is not None:
            programada = max(
                evento.fecha_devolucion - ANTICIPACION_RECORDATORIO,
                now,
            )

            notificaciones.append(
                NotificacionCreate(
                    **comunes,
                    codigo=construir_codigo(
                        "recordatorio_devolucion", evento.prestamo_id
                    ),
                    tipo="recordatorio_devolucion",
                    titulo="Recordatorio de devolución",
                    mensaje=(
                        f"Recuerda devolver {activo} antes de {fecha}."
                    ),
                    estado="pendiente",
                    fecha_programada=programada,
                )
            )

        return notificaciones

    if evento.evento == "prestamo_rechazado":
        motivo = f" Motivo: {evento.motivo}" if evento.motivo else ""

        return [
            NotificacionCreate(
                **comunes,
                codigo=construir_codigo(
                    "confirmacion_rechazo", evento.prestamo_id
                ),
                tipo="confirmacion_rechazo",
                titulo="Solicitud rechazada",
                mensaje=(
                    f"Tu solicitud de préstamo {del_activo} "
                    f"no fue aprobada.{motivo}"
                ),
                estado="enviada",
            )
        ]

    if evento.evento == "prestamo_por_vencer":
        return [
            NotificacionCreate(
                **comunes,
                codigo=construir_codigo(
                    "prestamo_por_vencer", evento.prestamo_id
                ),
                tipo="alerta_vencimiento",
                titulo="Préstamo próximo a vencer",
                mensaje=(
                    f"Tu préstamo {del_activo} está por vencer{limite}."
                ),
                estado="enviada",
            )
        ]

    if evento.evento == "prestamo_vencido":
        return [
            NotificacionCreate(
                **comunes,
                codigo=construir_codigo(
                    "prestamo_vencido", evento.prestamo_id
                ),
                tipo="alerta_vencimiento",
                titulo="Préstamo vencido",
                mensaje=(
                    f"Tu préstamo {del_activo} está vencido{limite}. "
                    "Devuélvelo lo antes posible."
                ),
                estado="enviada",
            )
        ]

    # prestamo_devuelto
    return [
        NotificacionCreate(
            **comunes,
            codigo=construir_codigo(
                "prestamo_devuelto", evento.prestamo_id
            ),
            tipo="notificacion_general",
            titulo="Devolución registrada",
            mensaje=f"Registramos la devolución {del_activo}. ¡Gracias!",
            estado="enviada",
        )
    ]


def tipos_a_cancelar(evento: EventoPrestamo) -> list[str]:
    return TIPOS_CANCELABLES.get(evento.evento, [])
