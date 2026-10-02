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
├── scripts/seed_activos.py  # Crea las colecciones e inserta 10 activos
├── tests/                   # Pruebas con pytest
├── pyproject.toml           # Dependencias (Poetry)
├── poetry.lock
├── Dockerfile
├── .dockerignore
└── docker-compose.yaml      # Para correrlo en local sin Kubernetes

kubernetes/equipo_2/
├── kind-config.yaml         # Cluster: 1 control-plane + 2 workers
├── namespace.yaml           # Namespace compartido proyecto-final
├── secret.yaml              # MONGO_URI hacia el Mongo común
├── backend_configmap.yaml   # Nombre de la base y de las colecciones
├── backend_deployment.yaml  # Deployment del API (2 réplicas) + Service
└── setup_app.sh             # Aplica todo en orden

.github/workflows/
└── categorias_ubicaciones_build_image.yaml  # CI/CD: build y push a GHCR
```

## Levantar todo desde cero

### Requisitos

- [Docker](https://www.docker.com/) con el daemon corriendo
- [kind](https://kind.sigs.k8s.io/) y `kubectl`
- [Poetry](https://python-poetry.org/) >= 2.0 (para el script de datos y las pruebas)

### 1. Crear el cluster y desplegar

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
