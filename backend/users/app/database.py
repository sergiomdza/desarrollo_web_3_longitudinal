from typing import Any

from app.config import setting
from pymongo import AsyncMongoClient
from pymongo.asynchronous.collection import AsyncCollection

cliente: AsyncMongoClient[dict[str, Any]] = AsyncMongoClient(setting.mongo_url)
db = cliente[setting.mongo_database]
usuarios_collection = db["auth_usuarios"]

async def save_document(collection: AsyncCollection[dict[str, Any]], document: dict[str, Any]) -> dict[str, Any]:
    resultado = await collection.insert_one(document)
    document["_id"] = resultado.inserted_id
    return document