# Categorías & Ubicaciones (Equipo 2)

Microservicio del sistema de gestión de activos institucionales que mantiene el
**catálogo de activos** de la institución: qué activos existen, a qué categoría
pertenecen, en qué ubicación física se encuentran y en qué estado están.

Está construido con **FastAPI**, guarda sus datos en **MongoDB** y se despliega
en un cluster local de **Kubernetes (kind)** con una imagen publicada en GHCR
por **GitHub Actions**.

## Entidad principal: Activo

Cada activo lleva su categoría y su ubicación embebidas en el mismo documento.

| Campo               | Tipo      | Reglas                                                     |
| ------------------- | --------- | ---------------------------------------------------------- |
| `id`                | string    | Lo genera MongoDB (solo en respuestas)                     |
| `codigo`            | string    | Obligatorio, 1–50 caracteres (ej. `TEC-001`)               |
| `nombre`            | string    | Obligatorio, 1–120 caracteres                              |
| `categoria`         | objeto    | `nombre` (obligatorio) y `descripcion` (opcional)          |
| `ubicacion`         | objeto    | `nombre` y `sede` (obligatorios), `piso` (opcional, ≥ 0)   |
| `estado`            | enum      | `disponible` (default), `en_uso`, `mantenimiento`, `baja`  |
| `valor_adquisicion` | número    | Obligatorio, mayor a 0                                     |
| `descripcion`       | string    | Opcional, hasta 500 caracteres                             |

Los modelos Pydantic están en [`models.py`](models.py) y validan tanto las
entradas como las salidas del API.

### Colecciones en MongoDB

Usamos el MongoDB común del namespace `proyecto-final`; nuestros datos viven en
la base de datos `equipo_2`, separada de la de los demás equipos:

| Colección     | Contenido                                |
| ------------- | ---------------------------------------- |
| `activos`     | Los activos del catálogo (CRUD del API)  |
| `categorias`  | Catálogo de categorías                   |
| `ubicaciones` | Catálogo de ubicaciones físicas          |

Los nombres de la base y de las colecciones se leen de variables de entorno
(`MONGO_DB_NAME`, `ACTIVOS_COLLECTION`, `CATEGORIAS_COLLECTION`,
`UBICACIONES_COLLECTION`), igual que la cadena de conexión `MONGO_URI`. Nada
de esto está escrito en el código: en Kubernetes llega por el ConfigMap
`categorias-ubicaciones-config` y el Secret `categorias-ubicaciones-secret`.

## Endpoints

| Método   | Ruta                  | Descripción                                                                                   | Respuestas      |
| -------- | --------------------- | --------------------------------------------------------------------------------------------- | --------------- |
| `GET`    | `/`                   | Mensaje de bienvenida del servicio                                                            | 200             |
| `GET`    | `/health`             | Indica si el servicio está vivo y si MongoDB responde                                         | 200             |
| `POST`   | `/activos`            | Crea un activo                                                                                | 201, 422        |
| `GET`    | `/activos`            | Lista los activos. Filtros opcionales: `estado`, `categoria`, `ubicacion`, `codigo`, `nombre` | 200, 422        |
| `GET`    | `/activos/{id}`       | Obtiene un activo por su ID                                                                   | 200, 404        |
| `PUT`    | `/activos/{id}`       | Actualiza un activo                                                                           | 200, 404, 422   |
| `DELETE` | `/activos/{id}`       | Elimina un activo                                                                             | 204, 404        |

Los filtros de texto (`categoria`, `ubicacion`, `codigo`, `nombre`) no
distinguen mayúsculas y aceptan coincidencias parciales, por ejemplo
`GET /activos?categoria=tecno&estado=disponible`.

La documentación interactiva (Swagger) está en `/docs`.

## Estructura de archivos

```text
backend/products/
├── main.py                  # App FastAPI y endpoints
├── models.py                # Modelos Pydantic
├── database.py              # Conexión a MongoDB (configuración por variables de entorno)
├── logging_config.py        # Logs en JSON (formatter + configuración de Uvicorn)
├── metrics.py               # Métricas de Prometheus y ruta /metrics
├── scripts/seed_activos.py  # Crea las colecciones e inserta 10 activos
├── tests/                   # Pruebas con pytest
├── pyproject.toml           # Dependencias (Poetry)
├── poetry.lock
├── Dockerfile
├── .dockerignore
└── docker-compose.yaml      # Para correrlo en local sin Kubernetes

kubernetes/
└── mongo_statefulset.yaml   # MongoDB común (StatefulSet + PVC 1Gi + Service)

kubernetes/equipo_2/
├── kind-config.yaml         # Cluster: 1 control-plane + 2 workers
├── namespace.yaml           # Namespace compartido proyecto-final
├── secret.yaml              # MONGO_URI hacia el Mongo común
├── backend_configmap.yaml   # Nombre de la base y de las colecciones
├── backend_deployment.yaml  # Deployment del API (2 réplicas) + Service
├── setup_app.sh             # Aplica todo en orden
└── observabilidad/          # Conexión con Prometheus y Alloy del stack de clase
    ├── metrics_service.yaml     # Service headless para raspar cada pod
    ├── prometheus_config.yaml   # Jobs del profesor + job categorias-ubicaciones
    ├── alloy_config.yaml        # Config del profesor + namespace proyecto-final
    ├── alloy_rbac.yaml          # Permisos de Alloy en proyecto-final
    ├── grafana_dashboard.json   # Dashboard del módulo, listo para importar en Grafana
    └── setup_observabilidad.sh  # Aplica todo y reinicia Prometheus y Alloy

.github/workflows/
└── categorias_ubicaciones_build_image.yaml  # CI/CD: build y push a GHCR
```

## Levantar todo desde cero

### Requisitos

- [Docker](https://www.docker.com/) con el daemon corriendo
- [kind](https://kind.sigs.k8s.io/) y `kubectl`
- [Poetry](https://python-poetry.org/) >= 2.0 (para el script de datos y las pruebas)

### 1. Crear el cluster y desplegar

> Si ya habías desplegado la versión anterior (namespace `equipo-2`), bórrala
> primero: `kubectl delete namespace equipo-2`.

Desde la raíz del repositorio:

```bash
cd kubernetes/equipo_2
./setup_app.sh
```

El script:

1. Crea el cluster de kind `web3` con `kind-config.yaml` (si no existe).
2. Aplica el namespace compartido `proyecto-final`.
3. Aplica el MongoDB común (`kubernetes/mongo_statefulset.yaml`: StatefulSet +
   PVC 1Gi + Service) y espera a que `mongo-0` esté listo.
4. Aplica el Secret, el ConfigMap y el Deployment del API (2 réplicas) con su
   Service.
5. Espera a que el Deployment termine su rollout.

El Deployment usa la imagen que publica el pipeline en
`ghcr.io/sergiomdza/categorias-ubicaciones` (para `linux/amd64` y
`linux/arm64`, así que funciona igual en Macs con Apple Silicon).

Verifica que todo esté corriendo:

```bash
kubectl get pods -n proyecto-final -l 'app in (mongo,categorias-ubicaciones)'
# mongo-0 y dos pods categorias-ubicaciones-api-... en estado Running
```

### 2. Exponer el API en tu máquina

En una terminal aparte (se queda corriendo):

```bash
kubectl port-forward -n proyecto-final service/categorias-ubicaciones-service 8000:8000
```

### 3. Cargar datos de prueba

El script se conecta al Mongo del cluster (lee el Secret y el ConfigMap y abre
su propio port-forward), crea las colecciones del módulo e inserta 10 activos.
Se puede correr varias veces sin duplicar datos.

```bash
cd backend/products
poetry install
poetry run python scripts/seed_activos.py
```

### 4. Probar el API

Abre http://localhost:8000/docs o usa `curl`:

```bash
# Salud del servicio
curl http://localhost:8000/health
# {"status":"ok","database":"ok"}

# Listar activos
curl http://localhost:8000/activos

# Crear un activo (201)
curl -X POST http://localhost:8000/activos \
  -H 'Content-Type: application/json' \
  -d '{
    "codigo": "TEC-010",
    "nombre": "Monitor Dell 27\"",
    "categoria": {"nombre": "Tecnología"},
    "ubicacion": {"nombre": "Biblioteca", "sede": "Campus Centro", "piso": 1},
    "estado": "disponible",
    "valor_adquisicion": 5200
  }'

# Obtener, actualizar y borrar (sustituye <id> por el "id" que devolvió el POST)
curl http://localhost:8000/activos/<id>
curl -X PUT http://localhost:8000/activos/<id> \
  -H 'Content-Type: application/json' \
  -d '{
    "codigo": "TEC-010",
    "nombre": "Monitor Dell 27\"",
    "categoria": {"nombre": "Tecnología"},
    "ubicacion": {"nombre": "Biblioteca", "sede": "Campus Centro", "piso": 1},
    "estado": "en_uso",
    "valor_adquisicion": 5200
  }'
curl -X DELETE http://localhost:8000/activos/<id>   # 204
curl http://localhost:8000/activos/<id>             # 404
```

### 5. Comprobar que los datos persisten

Borra el pod de Mongo y uno del backend. Cuando Kubernetes los recree, los
activos deben seguir ahí:

```bash
kubectl delete pod mongo-0 -n proyecto-final
kubectl delete pod -n proyecto-final <nombre-de-un-pod-categorias-ubicaciones-api>
kubectl rollout status statefulset/mongo -n proyecto-final
kubectl rollout status deployment/categorias-ubicaciones-api -n proyecto-final
curl http://localhost:8000/activos
```

Para ver los logs del API:

```bash
kubectl logs -n proyecto-final deployment/categorias-ubicaciones-api
```

### Correr en local sin Kubernetes (opcional)

```bash
cd backend/products
poetry run pytest                 # pruebas
docker compose up -d --build      # API + MongoDB en http://localhost:8000
docker compose down -v            # apagar y borrar datos
```

## Logs

Todo lo que el servicio escribe sale por la salida estándar en **JSON, una
línea por evento**, incluyendo los mensajes de Uvicorn. La configuración está en
[`logging_config.py`](logging_config.py) y `main.py` la aplica al arrancar.

```json
{"timestamp": "2026-11-14T23:44:23.379+00:00", "level": "INFO", "service": "categorias-ubicaciones", "logger": "categorias_ubicaciones", "message": "Activo creado", "activo_id": "6af8f257645f8381ea36531c", "codigo": "TEC-900", "status_code": 201}
```

| Campo       | Contenido                                                             |
| ----------- | --------------------------------------------------------------------- |
| `timestamp` | Fecha y hora del evento en UTC (ISO 8601)                             |
| `level`     | `INFO`, `WARNING`, `ERROR` o `CRITICAL`                               |
| `service`   | Nombre del servicio (`SERVICE_NAME`)                                  |
| `logger`    | Quién lo escribió: `categorias_ubicaciones` (nosotros) o `uvicorn.error` |
| `message`   | Qué pasó                                                              |
| otros       | Contexto que se pasa en `extra={...}`: `activo_id`, `status_code`...  |
| `exception` | Solo en errores: el traceback completo, dentro del mismo registro     |

- **Uvicorn también escribe en JSON:** le quitamos sus handlers de texto plano y
  sus mensajes (arranque, apagado, errores) pasan por nuestro formatter.
- **El access log de Uvicorn está apagado:** no hay una línea por cada request,
  así que `/health` y `/metrics` no generan ruido.
- **Los errores que tumban el proceso** (por ejemplo, falta una variable de
  entorno) y los warnings de Python también salen en JSON.
- **La URI de MongoDB nunca aparece:** el formatter la reemplaza por
  `mongodb://***` en el mensaje y en el traceback.

### Qué se registra y por qué

Los logs cuentan **qué le pasó a los activos** y **qué salió mal**; cuántas
requests hubo y cuánto tardaron ya lo dicen las métricas.

| Cuándo                                | Nivel     | `message`              | Contexto                                                        |
| ------------------------------------- | --------- | ---------------------- | --------------------------------------------------------------- |
| `POST /activos` crea (201)            | `INFO`    | `Activo creado`        | `activo_id`, `codigo`, `status_code`                            |
| `PUT /activos/{id}` actualiza (200)   | `INFO`    | `Activo actualizado`   | `activo_id`, `codigo`, `estado`, `status_code`                  |
| `DELETE /activos/{id}` elimina (204)  | `INFO`    | `Activo eliminado`     | `activo_id`, `status_code`                                      |
| GET/PUT/DELETE de un ID que no existe | `WARNING` | `Activo no encontrado` | `activo_id`, `operacion`, `status_code: 404`                    |
| Body o query inválido (422)           | `WARNING` | `Validación fallida`   | `operacion`, `errores` (campo + motivo, sin los valores)        |
| Falla de MongoDB (503 o 500)          | `ERROR`   | `Error de MongoDB`     | `operacion`, `error_type`, `mongo_code`, `error_detail` recortado |

- **Los cambios al catálogo van en `INFO`** con el `activo_id`, para poder
  reconstruir la historia de un activo sin leer el código.
- **404 y 422 van en `WARNING`, no en `ERROR`:** el servicio funcionó bien, fue
  el cliente el que pidió algo que no existe o mandó datos inválidos.
- **`ERROR` se reserva para fallas nuestras** (MongoDB caído o respondiendo con
  error), que son las que necesitan que alguien actúe. La causa va en el mismo
  JSON, sin traceback de varias líneas.
- **Los GET exitosos no se registran:** las lecturas no cambian nada y se
  repiten mucho; registrarlas sería ruido.
- **El 422 no incluye lo que mandó el cliente:** basta con saber qué campo falló
  y por qué; el body puede ser grande o traer datos que no queremos guardar.

Dos variables de entorno opcionales, definidas en el ConfigMap
`categorias-ubicaciones-config` y en `docker-compose.yaml`:

| Variable       | Valor por defecto        | Para qué sirve                    |
| -------------- | ------------------------ | --------------------------------- |
| `SERVICE_NAME` | `categorias-ubicaciones` | Campo `service` de cada log       |
| `LOG_LEVEL`    | `INFO`                   | Nivel mínimo que se escribe       |

## Métricas y observabilidad

El servicio expone métricas en formato Prometheus en `GET /metrics`. Están
definidas en [`metrics.py`](metrics.py); `main.py` solo llama a
`instrumentar(app)`.

| Métrica                         | Tipo      | Labels                 |
| ------------------------------- | --------- | ---------------------- |
| `http_requests_total`           | Counter   | `method`, `path`       |
| `http_responses_total`          | Counter   | `path`, `status_code`  |
| `http_request_duration_seconds` | Histogram | `method`, `path`       |
| `http_response_size_bytes`      | Histogram | `method`, `path`       |

- **`path` es la ruta plantilla** (`/activos/{activo_id}`), nunca el ID real:
  una serie por endpoint, no una por activo. Las rutas que no existen se
  registran como `sin_ruta`.
- **Histogramas** para poder calcular p95/p99 con `histogram_quantile`; un
  promedio esconde las requests lentas. Buckets de tamaño: 100 B a 100 KB.
- **`/health` y `/metrics` también se cuentan.** Los probes de Kubernetes llaman
  a `/health` cada 5 s, así que en los dashboards conviene filtrar
  `path!~"/health|/metrics"`.

### Conectarlo con Prometheus, Loki y Alloy

Requisitos en el namespace `default` (stack de clase, rama `main`):

- `kubernetes/monitoring_tools.yaml`: Prometheus y Grafana.
- `kubernetes/logging.yaml`: Loki y Alloy.

> ⚠️ En `monitoring_tools.yaml` el ConfigMap `grafana-config` dice
> `apiVersion: apps/v1` y falla al aplicarse. Apliquen ese bloque con
> `apiVersion: v1`; si no, Grafana no tiene el datasource de Loki.

Con el módulo ya desplegado (`setup_app.sh`):

```bash
./kubernetes/equipo_2/observabilidad/setup_observabilidad.sh
```

El script aplica los archivos de `observabilidad/` y reinicia Prometheus y
Alloy. `prometheus_config.yaml` y `alloy_config.yaml` son copias de la
configuración del profesor con nuestros cambios agregados: si el profesor
cambia la suya, hay que copiar sus cambios ahí antes de volver a aplicar.

**Cómo encuentra Prometheus los pods:** el Service
`categorias-ubicaciones-metrics` es headless (`clusterIP: None`), así que su
DNS devuelve la IP de cada pod en lugar de una IP que balancea. El job
`categorias-ubicaciones` usa `dns_sd_configs` sobre ese nombre y raspa cada
réplica por separado; con un Service normal, los contadores saltarían entre
réplicas.

**Cómo encuentra Alloy los logs:** su `discovery.kubernetes` busca también en
`proyecto-final` pods con `app=categorias-ubicaciones`. El Role y RoleBinding
`alloy-logs` de `alloy_rbac.yaml` le dan permiso de leerlos.

### Verificar

```bash
# Métricas de un pod
kubectl port-forward -n proyecto-final service/categorias-ubicaciones-service 8000:8000
curl -s localhost:8000/metrics | grep ^http_

# Prometheus -> http://localhost:9090/targets
# Debe mostrar el job categorias-ubicaciones con 2 endpoints en UP.
kubectl port-forward -n default service/prometheus-service 9090:9090

# Grafana -> http://localhost:3000 -> Explore -> Loki
# {app="categorias-ubicaciones"} debe traer logs de los 2 pods.
kubectl port-forward -n default service/grafana-service 3000:3000
```

### Dashboard de Grafana

El dashboard **Categorías & Ubicaciones** está guardado en
[`grafana_dashboard.json`](../../kubernetes/equipo_2/observabilidad/grafana_dashboard.json).
Todas sus consultas filtran por `app="categorias-ubicaciones"`, suman las 2
réplicas con `sum by (...)` y dejan fuera `/health` y `/metrics` para que los
probes no tapen el tráfico real.

| Panel                                    | Métrica                         | Consulta principal                                                                                                     |
| ---------------------------------------- | ------------------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| Requests por segundo, por método y ruta  | `http_requests_total`           | `sum by (method, path) (rate(http_requests_total{...}[1m]))`                                                           |
| Respuestas por status code               | `http_responses_total`          | `sum by (status_code) (increase(http_responses_total{...}[1m]))`                                                       |
| Respuestas por ruta y status code        | `http_responses_total`          | `sum by (path, status_code) (increase(http_responses_total{...}[$__range]))`                                           |
| Latencia p50 / p95 / p99                 | `http_request_duration_seconds` | `histogram_quantile(0.95, sum by (le) (rate(http_request_duration_seconds_bucket{...}[5m])))`                          |
| Latencia p95, por método y ruta          | `http_request_duration_seconds` | `histogram_quantile(0.95, sum by (le, method, path) (rate(http_request_duration_seconds_bucket{...}[5m])))`            |
| Tamaño promedio de respuesta             | `http_response_size_bytes`      | `sum by (method, path) (rate(..._sum{...}[5m])) / sum by (method, path) (rate(..._count{...}[5m]))`                    |
| Tamaño de respuesta p95                  | `http_response_size_bytes`      | `histogram_quantile(0.95, sum by (le, method, path) (rate(http_response_size_bytes_bucket{...}[5m])))`                 |
| Logs del servicio (extra)                | Loki                            | `{app="categorias-ubicaciones"}`                                                                                       |

Arriba hay una fila de resumen: réplicas en UP, requests por segundo, latencia
p95 y respuestas 4xx/5xx de los últimos 5 minutos.

- **`rate()` en lugar del contador directo:** el contador solo crece y vuelve a
  cero si el pod se reinicia. `rate()` lo convierte en requests por segundo y
  maneja esos reinicios.
- **p95:** el 95% de las requests tardó menos que ese valor. Muestra la
  experiencia de casi todos los usuarios sin que un caso extremo la distorsione.

#### Importarlo

1. Abre Grafana (el usuario y la contraseña están en el Secret `grafana-secret`
   de `monitoring_tools.yaml`):

   ```bash
   kubectl port-forward -n default service/grafana-service 3000:3000
   # http://localhost:3000
   ```

2. **Dashboards → New → Import → Upload dashboard JSON file** y elige
   `kubernetes/equipo_2/observabilidad/grafana_dashboard.json`. Luego **Import**.
3. Arriba del dashboard hay dos selectores, **Prometheus** y **Loki**: toman
   solos los datasources del stack de clase. El JSON no trae ningún ID de
   datasource fijo, por eso funciona igual en la máquina de cualquiera.

Los paneles necesitan tráfico para mostrar algo. Con el port-forward del API en
el puerto 8000 (paso 2 de "Levantar todo desde cero"), haz algunas requests
desde `/docs` o con los `curl` del paso 4: crear, listar, obtener, actualizar,
eliminar, un GET del ID borrado (404) y un POST inválido (422). En unos 15
segundos aparecen en el dashboard; el panel de status codes debe mostrar 200,
201, 204, 404 y 422 por separado.

## CI/CD

El workflow
[`categorias_ubicaciones_build_image.yaml`](../../.github/workflows/categorias_ubicaciones_build_image.yaml)
corre en cada push a la rama `equipo_2`: construye la imagen desde
`backend/products` para `linux/amd64` y `linux/arm64`, y la publica en GitHub
Container Registry con tres tags:

- el SHA corto del commit (ej. `c338e1e`), que identifica la versión exacta,
- el número de corrida del workflow,
- `latest`.

## Integrantes

| Integrante                       | Responsabilidad                                     |
| -------------------------------- | --------------------------------------------------- |
| Espinosa Rodríguez Alejandro     | Base del repo, configuración, `database.py`, health |
| Várguez Durán José Emilio        | Modelos Pydantic y CRUD de activos                  |
| Ortega Perera Santiago Martín    | Dockerfile, docker-compose y CI/CD                  |
| García Kuri Alejandro            | Manifiestos de Kubernetes y prueba de persistencia  |
| Gómez Montañez Vladimir Abraham  | Script de datos, documentación y evidencias         |
