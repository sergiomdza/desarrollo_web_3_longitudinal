
from pydantic import BaseModel, EmailStr, Field

#Roles (en caso de que exitan)


class UsersCreate (BaseModel):
    nombre: str = Field(min_length=1,max_length=50)
    apellido : str = Field(min_length=1,max_length=50)
    email : EmailStr 
    password : str = Field(min_length=8)
    #rol 
    
    
class UsersUpdate(BaseModel):
    nombre: str|None = None 
    apellido : str | None = None 
    email : str | None = None 
    activo: bool | None = None 
    #rol 
    
class UsersResponse(BaseModel):
    id : str 
    nombre : str 
    apellido : str 
    email : str 
    activo: bool 
    #rol 
    