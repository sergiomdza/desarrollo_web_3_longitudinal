"""Conexión a MongoDB y acceso a la colección del módulo."""
from pymongo import MongoClient

from config import MONGO_COLLECTION, MONGO_DB, MONGO_URI

mongo_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
reportes = mongo_client[MONGO_DB][MONGO_COLLECTION]