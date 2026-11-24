from enum import Enum

from pydantic import BaseModel, EmailStr, Field

# Roles (en caso de que exitan) Ya lei el documento y si hay roles


class UsersRoles(str, Enum):
    administrador = "Admin"
    Usuario = "Usuario"
    Moderador = "Mod"


class UsersCreate(BaseModel):
    nombre: str = Field(min_length=1, max_length=50)
    apellido: str = Field(min_length=1, max_length=50)
    email: EmailStr
    role: UsersRoles = UsersRoles.Usuario
    password: str = Field(min_length=8)


class UsersUpdate(BaseModel):
    nombre: str | None = None
    apellido: str | None = None
    email: str | None = None
    role: UsersRoles | None = None
    activo: bool | None = None


class UsersResponse(BaseModel):
    id: str
    nombre: str
    apellido: str
    email: str
    rol: UsersRoles
    activo: bool
