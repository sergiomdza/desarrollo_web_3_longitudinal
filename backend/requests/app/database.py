from pymongo import MongoClient

#aun no cambio el MongoClient por datos de un .env
mongo_client = MongoClient("mongodb://admin:web3@localhost:27017/?authSource=admin")
database = mongo_client["database_proyecto"]
requests_collection = database["requests"]
