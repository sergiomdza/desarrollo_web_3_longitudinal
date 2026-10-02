import os
from pymongo import MongoClient

MONGO_URI = os.getenv(
    "MONGO_URI",
    "mongodb://admin:web3@localhost:27017/?authSource=admin"
)

MONGO_DB_NAME = os.getenv(
    "MONGO_DB_NAME",
    "database_proyecto"
)

mongo_client = MongoClient(MONGO_URI)

database = mongo_client[MONGO_DB_NAME]

requests_collection = database["requests"]
