from fastapi import FastAPI
from app.routers import users

app = FastAPI(
    title="Usuarios y Autentificacion API",
    description="Usuarios,perfiles,roles y microservicio",
    version="1.00",
)

app.include_router(users.routers)


