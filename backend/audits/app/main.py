from fastapi import FastAPI, HTTPException
from prometheus_client import Histogram
from prometheus_fastapi_instrumentator import Instrumentator, metrics

from app.models import Auditoria, AuditoriaUpdate
from app.database import auditorias_collection


app = FastAPI()

# La librería trae el tamaño de respuesta como Summary; el proyecto lo pide como histograma.
response_size = Histogram(
    "http_response_size_bytes",
    "Tamaño de las respuestas HTTP en bytes.",
    ["handler", "method"],
    buckets=(64, 128, 256, 512, 1024, 2048, 4096, 8192, 16384, 65536, 262144, 1048576),
)

Instrumentator(
    should_group_status_codes=False,              # status exacto: 200, 201, 404, 422...
    should_ignore_untemplated=True,               # rutas inexistentes no crean series
    excluded_handlers=["^/health$", "^/metrics$"],
    should_instrument_requests_inprogress=True,   # requests en curso
    inprogress_labels=True,                       # ...por método y ruta
).add(
    metrics.requests()                            # total y por status code
).add(
    metrics.latency(should_include_status=False)  # latencia (histograma, segundos)
).add(
    lambda info: response_size.labels(info.modified_handler, info.method).observe(
        int(info.response.headers.get("Content-Length", 0))
    ) if info.response is not None else None     # tamaño de respuesta (histograma, bytes)
).instrument(app).expose(app, endpoint="/metrics")


@app.get("/")
def root():
    return {"message": "API del equipo de Auditorías funcionando"}


@app.get("/health")
def health_check():
    return {"status": "workflow funcionando correctamente"}

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