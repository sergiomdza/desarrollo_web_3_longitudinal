#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

poetry run python - <<'PY'
import asyncio
import runpy

from dotenv import load_dotenv
from pymongo import AsyncMongoClient
from app.Models.users import UsersCreate

load_dotenv("app/.env")

import os

async def main():
    roles = {
        "admin": "Admin",
        "usuario": "Usuario",
        "moderador": "Mod",
    }

    usuarios = runpy.run_path("app/seed_usurios.py")["usuarios"]
    modelos = [
        UsersCreate.model_validate({
            **usuario,
            "role": roles[usuario["rol"]],
        })
        for usuario in usuarios
    ]

    async with AsyncMongoClient(os.environ["MONGO_URL"]) as client:
        db = client[os.environ["MONGO_DATABASE"]]

        if "auth_usuarios" not in await db.list_collection_names():
            await db.create_collection("auth_usuarios")

        collection = db["auth_usuarios"]

        for usuario in modelos:
            datos = usuario.model_dump(mode="json", exclude={"password"})
            datos["activo"] = True

            resultado = await collection.update_one(
                {"email": datos["email"]},
                {"$setOnInsert": datos},
                upsert=True,
            )

            estado = "CREADO" if resultado.upserted_id else "YA EXISTE"
            print(f"[{estado}] {datos['email']}")

asyncio.run(main())
PY