from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator
from .routers import requests_router, health_router

app = FastAPI()

Instrumentator().instrument(app).expose(app, endpoint="/metrics")

app.include_router(health_router.router)
app.include_router(requests_router.router)
