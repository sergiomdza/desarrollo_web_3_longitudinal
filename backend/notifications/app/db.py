import os
from urllib.parse import quote_plus

from pymongo import AsyncMongoClient
from pymongo.errors import ServerSelectionTimeoutError


COLLECTION_NAME = "notificaciones"

_client = None
_database = None


def require_env(name: str) -> str:
    value = os.getenv(name)

    if not value:
        raise RuntimeError(
            f"La variable de entorno '{name}' es obligatoria."
        )

    return value


def build_mongo_uri() -> str:
    host = require_env("MONGO_HOST")
    port = require_env("MONGO_PORT")
    username = quote_plus(require_env("MONGO_USERNAME"))
    password = quote_plus(require_env("MONGO_PASSWORD"))
    auth_source = require_env("MONGO_AUTH_SOURCE")

    return (
        f"mongodb://{username}:{password}"
        f"@{host}:{port}/"
        f"?authSource={auth_source}"
    )


async def connect_to_mongo() -> None:
    global _client, _database

    mongo_uri = build_mongo_uri()

    _client = AsyncMongoClient(
        mongo_uri,
        serverSelectionTimeoutMS=5000,
    )

    try:
        await _client.admin.command("ping")
    except ServerSelectionTimeoutError as exc:
        await _client.close()
        _client = None
        raise RuntimeError(
            "No fue posible conectar con MongoDB."
        ) from exc

    database_name = require_env("MONGO_DB")

    _database = _client[database_name]

    await _database[COLLECTION_NAME].create_index(
        "codigo",
        unique=True,
    )


async def close_mongo() -> None:
    global _client, _database

    if _client is not None:
        await _client.close()

    _client = None
    _database = None


def get_database():
    if _database is None:
        raise RuntimeError(
            "La conexión con MongoDB no está inicializada."
        )

    return _database