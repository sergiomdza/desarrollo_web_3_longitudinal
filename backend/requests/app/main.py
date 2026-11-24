from fastapi import FastAPI
from .metrics import setup_metrics
from .routers import requests_router, health_router

app = FastAPI()

setup_metrics(app)

app.include_router(health_router.router)
app.include_router(requests_router.router)
