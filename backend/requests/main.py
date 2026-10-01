import os
from fastapi import FastAPI
from pymongo import MongoClient
from prometheus_fastapi_instrumentator import Instrumentator

app = FastAPI()

Instrumentator().instrument(app).expose(app, endpoint="/metrics")

#aun no cambio el MongoClient por datos de un .env 
mongo_client = MongoClient("mongodb://admin:web3@localhost:27017/?authSource=admin")
database = mongo_client["database_proyecto"]
prueba = database["test"]

@app.get("/")
def default():
    return {"status": "Uvicorn server running"}

#get de health para comrprovar que anda vivo el fastapi
@app.get("/health")
def health_check():
    return {"status": "ok"}

#prueba para ver que se conecte a la base de datos
@app.get("/get_test")
def get_prueba():
    return list(prueba.find({}, {"_id": 0}))
