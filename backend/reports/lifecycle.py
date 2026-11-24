"""Logs de inicio y apagado del servicio."""
import logging
from contextlib import asynccontextmanager

from pymongo.errors import PyMongoError

from config import MONGO_COLLECTION, MONGO_DB
from database import mongo_client

logger = logging.getLogger("reportes.lifecycle")


@asynccontextmanager
async def lifespan(app):
    logger.info("Servicio iniciado", extra={"mongo_db": MONGO_DB, "mongo_collection": MONGO_COLLECTION})
    try:
        mongo_client.admin.command("ping")
        logger.info("Conexión a MongoDB verificada")
    except PyMongoError as exc:
        logger.error("No se pudo conectar a MongoDB al iniciar", exc_info=exc)
    yield
    mongo_client.close()
    logger.info("Servicio detenido")