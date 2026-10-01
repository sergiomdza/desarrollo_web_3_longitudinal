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



@routers.post("/create")
async def create_user(user: dict):
    return {"message": "Usuario creado exitosamente", "user": user}
# crud de post

@routers.get("/get")
async def get_users():
    return {"message": "Usuarios obtenidos exitosamente", "users": []}

@routers.get("/get/{user_id}")
async def get_user_by_id(user_id: str):
    return {"message": "Usuario obtenido exitosamente", "user_id": user_id}
# crud de get

# crud de put


# crud de delate
