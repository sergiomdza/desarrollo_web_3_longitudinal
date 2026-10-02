"""Punto de entrada: crea la app, expone métricas y registra los routers."""
from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator

from routers import reportes

app = FastAPI(
    title="Reportes y Analítica",
    description="Microservicio de estadísticas de uso del sistema de gestión de activos.",
)
Instrumentator().instrument(app).expose(app, endpoint="/metrics")

app.include_router(reportes.router)


@app.get("/health")
def health_check():
    return {"status": "ok"}