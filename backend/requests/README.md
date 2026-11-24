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

-------------------------------------------
PARCIAL 2
## Contrato de observabilidad (Proyecto 2)

### Identificación del servicio
- Label `app` del pod y valor de `service` en los logs: `requests-backend`
    (Se requiere cambiar el label por que el stack de monitoreo del profe lo busca como `requests-backend`
                                                                v
                                                                v
                                                                v    
    label = "app in (products-backend,users-backend,requests-backend,reports-backend,audits-backend,notifications-backend)" )
- Se configura en el ConfigMap con la variable `SERVICE_NAME`

### Métricas (endpoint `/metrics`)
| Métrica | Tipo | Labels |
|---|---|---|
| `http_requests_total` | counter | app, method, handler, status |
| `http_request_duration_seconds` | histogram | app, method, handler |
| `http_response_size_bytes` | histogram | app, method, handler |

- `handler` es la plantilla de la ruta (`/requests/{id}`), nunca el ID real.
- `status` es el código exacto (200, 201, 404, 422, 500), no agrupado (2xx).
- No se miden `/health` ni `/metrics`.

### Logs
- JSON, una línea por evento, en stdout.
- Campos obligatorios: `timestamp`, `level`, `service`, `message`.
- Campos de contexto cuando apliquen: `request_id`, `method`, `path`,
  `status_code`, `duration_ms`, `error`.
- Niveles: INFO (crear/actualizar/eliminar, inicio/apagado),
  WARNING (no encontrado, validación fallida), ERROR (fallas de MongoDB).
- No se loggea: `/health`, `/metrics`, access log de uvicorn,
  credenciales ni la URI de MongoDB.

Prometheus

1. Desde la raíz del repositorio, seleccionar el contexto de Kubernetes:
   kubectl config use-context kind-web3
2. Aplicar el manifiesto compartido que contiene el ConfigMap:
   kubectl apply -f kubernetes/monitoring_tools.yaml
3. Reiniciar Prometheus para cargar la configuración:
   kubectl rollout restart deployment/prometheus -n default
4. Verificar que Prometheus esté disponible:
   kubectl get pods -n default -l app=prometheus
5. Habilitar el acceso local:
   kubectl port-forward -n default svc/prometheus-service 9090:9090
6. Abrir http://localhost:9090/targets y localizar el job solicitudes.
7. Comprobar consultas (prometheus_queries.md).

Grafana

1. Stack compartido (Prometheus, Grafana, Loki, Alloy):
   kubectl apply -f kubernetes/monitoring_tools.yaml
   kubectl apply -f kubernetes/logging.yaml
2. Nuestro servicio:
   kubectl apply -f kubernetes/requests/backend_configmap.yaml
   kubectl apply -f kubernetes/requests/backend_deployment.yaml
3. Abrir Grafana:
   kubectl port-forward svc/grafana-service 3000:3000
   http://localhost:3000 (usuario: grafana_admin / contraseña: web3)
4. Importar el dashboard: Dashboards → New → Import → subir
   `kubernetes/requests/grafana-dashboard.json` → Import.

Si tenías desplegado el servicio del Proyecto 1, bórralo antes del paso 2:
   kubectl delete deployment backend-requests -n proyecto-final
   kubectl delete service backend-requests-service -n proyecto-final
