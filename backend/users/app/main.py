from fastapi import FastAPI

app = FastAPI(
    title="Usuarios y Autentificacion API",
    description="Usuarios,perfiles,roles y microservicio",
    version="1.00",
)
# se descomentara cuando este los ends
# app.include_router(routers)


@app.get("/helth")
async def helth():
    return {"status": "bien", "services": "users"}
