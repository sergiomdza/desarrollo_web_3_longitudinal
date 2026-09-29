from fastapi import FastAPI, HTTPException
from prometheus_fastapi_instrumentator import Instrumentator

from app.models import Auditoria, AuditoriaUpdate
from app.database import auditorias_collection


app = FastAPI()

Instrumentator().instrument(app).expose(app, endpoint="/metrics")


@app.get("/")
def root():
    return {"message": "API de Auditorías funcionando"}


@app.get("/health")
def health_check():
    return {"status": "ok"}

## Crud basico

@app.get("/auditorias", response_model=list[Auditoria])
def get_auditorias():
    return list(auditorias_collection.find({},{"_id": 0}))

@app.get("/auditorias/{id}", response_model=Auditoria)
def get_auditoria(id: int):
    
    auditoria = auditorias_collection.find_one(
        {"id": id},
        {"_id": 0}
    )

    if auditoria is None: 
        raise HTTPException(status_code=404,detail="Auditoría no encontrada")

    return auditoria

@app.post("/auditorias", response_model=Auditoria, status_code=201)
def create_auditoria(auditoria: Auditoria):

    if auditorias_collection.find_one({"id": auditoria.id}):
        raise HTTPException(status_code=409,detail="Ya existe una auditoría con ese ID")

    auditorias_collection.insert_one(auditoria.model_dump())

    return auditoria

@app.put("/auditorias/{id}", response_model=Auditoria)
def update_auditoria(id: int, auditoria: AuditoriaUpdate):

    if auditorias_collection.find_one({"id": id}) is None:
        raise HTTPException(status_code=404,detail="Auditoría no encontrada")

    datos = auditoria.model_dump(exclude_unset=True)

    if datos:
        auditorias_collection.update_one({"id": id},{"$set": datos})

    return auditorias_collection.find_one({"id": id},{"_id": 0})

@app.delete("/auditorias/{id}", status_code=200)
def delete_auditoria(id: int):
    
    resultado = auditorias_collection.delete_one({"id": id})

    if resultado.deleted_count == 0:
        raise HTTPException(status_code=404,detail="Auditoría no encontrada")

    return {"message": "Auditoría eliminada correctamente"}