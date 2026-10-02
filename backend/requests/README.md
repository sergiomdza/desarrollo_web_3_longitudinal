Equipo #4

Descripcion del modulo:

Tabla de enpoints:

Instrucciones para levantar:
Para crear el namespace si no lo tienes creado aplica kubectl create namespace proyecto-final
Si quieres corroborar que lo tengas utiliza kubectl get namespaces
Para ejecutar el dockerfile ubicate dentro de la carpeta de /requests y realiza el comando.
docker build -t backend_requests

Cluster:

Aplicar manifiestos:

Probar API:
1.Primero ejecutar este comando en una terminal que apunte a /kubernetes
kubectl port-forward svc/mongo-service 27017:27017 -n proyecto-final
2.Despues correr el crud en una terminal que a punte a /requests
poetry run uvicorn app.main:app --reload


Integrantes del equipo:
CAMPOS DAGUER EMILIO
COBOS BRACAMONTE JOSHUA ARTURO
GUILLERMO PIÑA ANDERSON
ROSADO SANTIAGO ANGEL EFREN
YUPIT BENITEZ ROBERTO