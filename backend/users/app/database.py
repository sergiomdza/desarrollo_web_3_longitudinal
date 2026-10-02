from typing import Any

from app.config import setting
from pymongo import AsyncMongoClient

cliente: AsyncMongoClient[dict[str, Any]] = AsyncMongoClient(setting.mongo_url)
db = cliente[setting.mongo_database]
usuarios_collection = db["auth_usuarios"]
