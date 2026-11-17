"""Punto de entrada: crea la app, configura logging y métricas y registra los routers."""
from fastapi import FastAPI

from logging_config import setup_logging

setup_logging()  # primero: todo lo que se importe después ya usa el logger JSON

from errors import register_error_handlers  # noqa: E402
from lifecycle import lifespan  # noqa: E402
from metrics import setup_metrics  # noqa: E402
from middleware import RequestContextMiddleware  # noqa: E402
from routers import reportes  # noqa: E402

app = FastAPI(
    title="Reportes y Analítica",
    description="Microservicio de estadísticas de uso del sistema de gestión de activos.",
    lifespan=lifespan,
)

app.add_middleware(RequestContextMiddleware)
setup_metrics(app)
register_error_handlers(app)
app.include_router(reportes.router)


@app.get("/health")
def health_check():
    return {"status": "ok"}