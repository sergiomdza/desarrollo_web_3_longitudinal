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

@app.get("/users")
async def get_users():
    return {"users": []}

@app.get("/users/{user_id}")
async def get_user(user_id: int):
    return {"user_id": user_id, "name": "John Doe"}
