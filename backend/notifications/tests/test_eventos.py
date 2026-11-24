from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from app.eventos import construir_notificaciones, tipos_a_cancelar
from app.models import EventoPrestamo


NOW = datetime(2026, 10, 1, 12, 0, tzinfo=timezone.utc)


def evento(**kwargs) -> EventoPrestamo:
    datos = {
        "evento": "prestamo_aprobado",
        "prestamo_id": "PREST-001",
        "usuario_id": "USR-001",
        "activo_nombre": "Laptop Dell",
    }
    datos.update(kwargs)
    return EventoPrestamo(**datos)


def test_aprobado_con_fecha_crea_confirmacion_y_recordatorio():
    devolucion = NOW + timedelta(days=7)

    confirmacion, recordatorio = construir_notificaciones(
        evento(fecha_devolucion=devolucion), NOW
    )

    assert confirmacion.tipo == "confirmacion_aprobacion"
    assert confirmacion.estado == "enviada"
    assert confirmacion.codigo == "APR-PREST-001"
    assert "del activo «Laptop Dell»" in confirmacion.mensaje

    assert recordatorio.tipo == "recordatorio_devolucion"
    assert recordatorio.estado == "pendiente"
    assert recordatorio.codigo == "REC-PREST-001"
    assert recordatorio.fecha_programada == devolucion - timedelta(days=1)


def test_aprobado_sin_fecha_no_programa_recordatorio():
    notificaciones = construir_notificaciones(evento(), NOW)

    assert [n.tipo for n in notificaciones] == ["confirmacion_aprobacion"]


def test_recordatorio_no_se_programa_en_el_pasado():
    devolucion = NOW + timedelta(hours=2)

    _, recordatorio = construir_notificaciones(
        evento(fecha_devolucion=devolucion), NOW
    )

    assert recordatorio.fecha_programada == NOW


def test_fecha_sin_zona_horaria_se_asume_utc():
    e = evento(fecha_devolucion=datetime(2026, 10, 8, 12, 0))

    assert e.fecha_devolucion.tzinfo == timezone.utc


def test_rechazado_incluye_motivo():
    (notificacion,) = construir_notificaciones(
        evento(evento="prestamo_rechazado", motivo="Sin stock"), NOW
    )

    assert notificacion.tipo == "confirmacion_rechazo"
    assert notificacion.codigo == "RCH-PREST-001"
    assert "Sin stock" in notificacion.mensaje


@pytest.mark.parametrize(
    ("tipo_evento", "codigo", "titulo"),
    [
        ("prestamo_por_vencer", "PVN-PREST-001", "Préstamo próximo a vencer"),
        ("prestamo_vencido", "VEN-PREST-001", "Préstamo vencido"),
    ],
)
def test_alertas_de_vencimiento(tipo_evento, codigo, titulo):
    (notificacion,) = construir_notificaciones(
        evento(evento=tipo_evento), NOW
    )

    assert notificacion.tipo == "alerta_vencimiento"
    assert notificacion.codigo == codigo
    assert notificacion.titulo == titulo


def test_devuelto_crea_confirmacion_general():
    (notificacion,) = construir_notificaciones(
        evento(evento="prestamo_devuelto"), NOW
    )

    assert notificacion.tipo == "notificacion_general"
    assert notificacion.codigo == "DEV-PREST-001"


def test_tipos_a_cancelar():
    assert tipos_a_cancelar(evento(evento="prestamo_aprobado")) == []
    assert tipos_a_cancelar(evento(evento="prestamo_vencido")) == [
        "recordatorio_devolucion"
    ]
    assert "alerta_vencimiento" in tipos_a_cancelar(
        evento(evento="prestamo_devuelto")
    )


def test_prestamo_id_demasiado_largo_se_rechaza():
    with pytest.raises(ValidationError):
        evento(prestamo_id="X" * 47)


def test_mismo_evento_genera_mismo_codigo():
    a = construir_notificaciones(evento(evento="prestamo_vencido"), NOW)
    b = construir_notificaciones(evento(evento="prestamo_vencido"), NOW)

    assert a[0].codigo == b[0].codigo
