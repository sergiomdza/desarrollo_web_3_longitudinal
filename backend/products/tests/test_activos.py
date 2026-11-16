import pytest
from pydantic import ValidationError

from models import Activo, Categoria, EstadoActivo, Ubicacion


def test_activo_validacion_basica():
    activo = Activo(
        id="66f0d0b5e0f1d3d4ab12cd34",
        codigo="ACT-001",
        nombre="Laptop Lenovo",
        categoria=Categoria(nombre="Tecnología", descripcion="Equipo de cómputo"),
        ubicacion=Ubicacion(nombre="Oficina Central", sede="Bogotá", piso=2),
        estado=EstadoActivo.DISPONIBLE,
        valor_adquisicion=1500.0,
        descripcion="Laptop para desarrollo",
    )

    assert activo.codigo == "ACT-001"
    assert activo.estado == EstadoActivo.DISPONIBLE


def test_activo_rechaza_valor_adquisicion_no_positivo():
    with pytest.raises(ValidationError):
        Activo(
            id="66f0d0b5e0f1d3d4ab12cd35",
            codigo="ACT-002",
            nombre="Monitor",
            categoria=Categoria(nombre="Tecnología"),
            ubicacion=Ubicacion(nombre="Sala de reuniones", sede="Bogotá", piso=1),
            estado=EstadoActivo.EN_USO,
            valor_adquisicion=0,
        )
