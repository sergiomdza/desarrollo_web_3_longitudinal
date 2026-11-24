from app.database import usuarios_collection, save_document
from ..Models.users import UsersCreate, UsersResponse
from ..routers.users import usuario_dict

class UserService:
    async def read_user_by_id(self, user_id: str) -> UsersResponse | None:
        filtro = {"$expr": {"$eq": [{"$toString": "$_id"}, user_id]}}
        usuario = await usuarios_collection.find_one(filtro)
        if not usuario:
            return None
        return usuario_dict(usuario)

    async def read_user_by_email(self, email: str) -> dict | None:
        return await usuarios_collection.find_one({"email": email})

    async def read_all_users(self) -> list[UsersResponse]:
        usuarios = []
        async for usuario in usuarios_collection.find({}):
            usuarios.append(usuario_dict(usuario))
        return usuarios

    async def create_user(self, new_user_data: UsersCreate, hashed_password: str) -> UsersResponse:
        nuevo_usuario = {
            "nombre": new_user_data.nombre,
            "apellido": new_user_data.apellido,
            "email": str(new_user_data.email),
            "password_hash": hashed_password,
            "role": new_user_data.role.value,
            "activo": True,
        }
        saved_doc = await save_document(usuarios_collection, nuevo_usuario)
        return usuario_dict(saved_doc)