Equipo #4

Descripcion del modulo: El módulo esta destinado a gestionar solicitudes y préstamos de activos realizadas por el sistema. Este módulo nos permite crear, actualizar, eliminar y consultar en las distintas peticiones de los usuarios. Las distintas petiviones se encuentran en una base de datos.

Tabla de enpoints:
health_router // GET que recibe el status para saber si esta funcionando.

request_router:
GET Requests // Consulta los request de la bd en general.
POST Requests // Generas un request llenando los datos.
GET Requests {id} // Consulta el request de la bd que contenga el ID ingresado.
PUT Requests // Actualiza el request ingresado.
DELETE Requests // Elimina el request ingresado por ID.

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

Ejecutar script para crear la tabla "Requests" y poblarlo:
1. Ir al dirrectorio de requests
cd backend
cd requests
2. poetry run python create_table_mongo.py

Integrantes del equipo:
CAMPOS DAGUER EMILIO
COBOS BRACAMONTE JOSHUA ARTURO
GUILLERMO PIÑA ANDERSON
ROSADO SANTIAGO ANGEL EFREN
YUPIT BENITEZ ROBERTO