from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator
#por cada router nuevo agregado aqui poner el archivo
#y tambien colocar un app.include_router
from .routers import obtain_health, obtain_requests

app = FastAPI()

Instrumentator().instrument(app).expose(app, endpoint="/metrics")

app.include_router(obtain_health.router)
app.include_router(obtain_requests.router)
