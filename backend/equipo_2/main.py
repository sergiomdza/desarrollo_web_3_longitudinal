from fastapi import FastAPI

import database

app = FastAPI(
    title="Categorías & Ubicaciones",
    description="Catálogo de activos: tipos de activos, ubicaciones físicas y disponibilidad por ubicación (Equipo 2).",
    version="0.1.0",
)


@app.get("/")
def default():
    return {"message": "Servicio de Categorías & Ubicaciones - Equipo 2"}


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "database": "ok" if database.ping() else "unreachable",
    }
