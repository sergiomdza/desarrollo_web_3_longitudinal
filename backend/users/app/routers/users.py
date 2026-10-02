from fastapi import APIRouter, HTTPException, status

from app.Models.users import UsersCreate, UsersResponse, UsersRoles, UsersUpdate
from app.database import usuarios_collection

routers = APIRouter(prefix="/usuarios", tags=["Users"])


def usuario_dict(usuario: dict) -> UsersResponse:
    return UsersResponse(
        id=str(usuario.get("_id", "")),
        nombre=str(usuario["nombre"]),
        apellido=str(usuario["apellido"]),
        email=str(usuario["email"]),
        rol=UsersRoles(usuario.get("role", UsersRoles.Usuario.value)),
        activo=bool(usuario.get("activo", True)),
    )


@routers.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    return {"status": "ESTOY VIVO :D"}


@routers.get("/", response_model=list[UsersResponse])
async def get_users():
    usuarios = []
    async for usuario in usuarios_collection.find({}):
        usuarios.append(usuario_dict(usuario))
    return usuarios


@routers.get("/{user_id}", response_model=UsersResponse)
async def get_user(user_id: str):
    filtro = {"$expr": {"$eq": [{"$toString": "$_id"}, user_id]}}
    usuario = await usuarios_collection.find_one(filtro)
    if usuario is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Usuario con id {user_id} no encontrado",
        )
    return usuario_dict(usuario)



@routers.post("/create", response_model=UsersResponse, status_code=status.HTTP_201_CREATED)
async def create_user(user: UsersCreate):
    nuevo_usuario = {
        "nombre": user.nombre,
        "apellido": user.apellido,
        "email": str(user.email),
        "role": user.role.value,
        "activo": True,
    }
    resultado = await usuarios_collection.insert_one(nuevo_usuario)
    nuevo_usuario["_id"] = resultado.inserted_id
    return usuario_dict(nuevo_usuario)


@routers.put("/update/{user_id}", response_model=UsersResponse)
async def update_user(user_id: str, user: UsersUpdate):
    filtro = {"$expr": {"$eq": [{"$toString": "$_id"}, user_id]}}
    datos_actualizados = user.model_dump(
        exclude_unset=True,
        exclude_none=True,
        mode="json",
    )

    if datos_actualizados:
        resultado = await usuarios_collection.update_one(
            filtro,
            {"$set": datos_actualizados},
        )
        if resultado.matched_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Usuario con id {user_id} no encontrado",
            )

    usuario_actualizado = await usuarios_collection.find_one(filtro)
    if usuario_actualizado is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Usuario con id {user_id} no encontrado",
        )
    return usuario_dict(usuario_actualizado)


@routers.delete("/delete/{user_id}", status_code=status.HTTP_200_OK)
async def delete_user(user_id: str):
    filtro = {"$expr": {"$eq": [{"$toString": "$_id"}, user_id]}}
    resultado = await usuarios_collection.delete_one(filtro)
    if resultado.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Usuario con id {user_id} no encontrado",
        )

    return {"message": "Usuario eliminado exitosamente", "user_id": user_id}
