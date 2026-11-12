import os
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB = os.getenv("MONGO_DB")
MONGO_COLLECTION = os.getenv("MONGO_COLLECTION")

if not MONGO_URI:
    raise RuntimeError("La variable de entorno MONGO_URI no está definida")

if not MONGO_DB:
    raise RuntimeError("La variable de entorno MONGO_DB no está definida")

if not MONGO_COLLECTION:
    raise RuntimeError("La variable de entorno MONGO_COLLECTION no está definida")


mongo_client = MongoClient(MONGO_URI)

database = mongo_client[MONGO_DB]
auditorias_collection = database[MONGO_COLLECTION]