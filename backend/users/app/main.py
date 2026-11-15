from fastapi import FastAPI
from app.routers import users, auth_routers
from prometheus_fastapi_instrumentator import Instrumentator

app = FastAPI(
    title="Usuarios y Autentificacion API",
    description="Usuarios,perfiles,roles y microservicio",
    version="1.00",
)
Instrumentator ().instrument(app).expose(app,endpoint="/metrics")



app.include_router(users.routers)
app.include_router(auth_routers.router)
