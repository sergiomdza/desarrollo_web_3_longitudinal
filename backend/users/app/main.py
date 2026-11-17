from fastapi import FastAPI
from app.routers import users, auth_routers
from app.metrics import custom_metrics
from app.logs import setup_logging, log_requests
from prometheus_fastapi_instrumentator import Instrumentator

setup_logging()

app = FastAPI(
    title="Usuarios y Autentificacion API",
    description="Usuarios,perfiles,roles y microservicio",
    version="1.00",
)

app.middleware("http")(log_requests)

instrumentator = Instrumentator(
    should_group_status_codes=False,
    should_ignore_untemplated=True,
    should_instrument_requests_inprogress=True,
    inprogress_labels=True,
    excluded_handlers=["/metrics", "/docs", "/usuarios/health", "/openapi.json"],
    body_handlers=[".*"],
)

instrumentator.add(custom_metrics)

instrumentator.instrument(app).expose(app, endpoint="/metrics")

app.include_router(users.routers)
app.include_router(auth_routers.router)
