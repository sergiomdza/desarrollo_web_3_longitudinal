# Apartado de los cruds

from fastapi import APIRouter

routers = APIRouter(prefix="/usuarios", tags=["Users"])


def usuario_dict(usuario) -> dict:
    return {
        "id": str(usuario["_id"]),
        "nombre": str(usuario["nombre"]),
        "apellido": str(usuario["apellido"]),
        "email": str(usuario["email"]),
        "role": str(usuario["role"]),
        "activo": str(usuario["activo"]),
    }


# crud de post


# crud de get

# crud de put


# crud de delate
