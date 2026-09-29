import os

from pymongo import MongoClient


def _required_env(name: str) -> str:
    """Lee una variable de entorno obligatoria; falla al arrancar si no existe."""
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Falta la variable de entorno requerida: {name}")
    return value


# Configuración (en Kubernetes llega vía Secret / ConfigMap)
MONGO_URI = _required_env("MONGO_URI")
MONGO_DB_NAME = _required_env("MONGO_DB_NAME")
CATEGORIAS_COLLECTION = _required_env("CATEGORIAS_COLLECTION")
UBICACIONES_COLLECTION = _required_env("UBICACIONES_COLLECTION")

# Mongo DB connection
mongo_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000)
database = mongo_client[MONGO_DB_NAME]
categorias = database[CATEGORIAS_COLLECTION]
ubicaciones = database[UBICACIONES_COLLECTION]


def ping() -> bool:
    """Regresa True si MongoDB responde."""
    try:
        mongo_client.admin.command("ping")
        return True
    except Exception:
        return False
