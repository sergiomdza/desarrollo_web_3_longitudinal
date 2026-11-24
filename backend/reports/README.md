# Módulo Reportes y Analítica

Microservicio del sistema de gestión de activos institucionales, responsable de las **estadísticas de uso**: registra y consulta reportes sobre el uso de activos, préstamos, inventario y mantenimientos.

Construido con **FastAPI**, **MongoDB** y **Poetry**; empaquetado en una imagen Docker por un pipeline de **GitHub Actions** y desplegado en un cluster de **Kubernetes local (Kind)**.

## Entidad implementada: `reporte`

| Campo            | Tipo                        | Descripción                                                   |
| ---------------- | --------------------------- | ------------------------------------------------------------- |
| `id`             | string                      | Identificador generado por MongoDB (solo en respuestas)       |
| `titulo`         | string (3–120)              | Título del reporte                                            |
| `tipo`           | enum                        | `uso_activos`, `prestamos`, `inventario` o `mantenimiento`    |
| `descripcion`    | string (opcional, máx. 500) | Descripción del reporte                                       |
| `periodo_inicio` | datetime                    | Inicio del periodo analizado                                  |
| `periodo_fin`    | datetime                    | Fin del periodo analizado                                     |
| `generado_por`   | string (mín. 2)             | Usuario que generó el reporte                                 |
| `metricas`       | objeto `{nombre: número}`   | Métricas calculadas (por ejemplo, `total_prestamos`)          |
| `creado_en`      | datetime                    | Fecha de creación (solo en respuestas, la asigna el servidor) |

Los datos se guardan en la colección `reportes_analitica`, propia de este módulo.

## Endpoints

| Método   | Ruta             | Descripción                                  | Códigos de estado |
| -------- | ---------------- | -------------------------------------------- | ----------------- |
| `GET`    | `/health`        | Indica si el servicio está vivo              | 200               |
| `GET`    | `/metrics`       | Métricas de Prometheus                       | 200               |
| `GET`    | `/docs`          | Documentación interactiva (Swagger UI)       | 200               |
| `POST`   | `/reportes`      | Crea un reporte                              | 201, 422          |
| `GET`    | `/reportes`      | Lista reportes (parámetros `skip` y `limit`) | 200, 422          |
| `GET`    | `/reportes/{id}` | Obtiene un reporte por ID                    | 200, 404, 422     |
| `PUT`    | `/reportes/{id}` | Actualiza los campos enviados de un reporte  | 200, 404, 422     |
| `DELETE` | `/reportes/{id}` | Elimina un reporte                           | 204, 404, 422     |

## Estructura del módulo

```
backend/reports/
├── main.py              # App FastAPI, /health, /metrics y registro del router
├── config.py            # Variables de entorno
├── database.py          # Conexión a MongoDB y colección
├── schemas.py           # Modelos Pydantic
├── utils.py             # Conversión de documentos y validación de IDs
├── routers/
│   └── reportes.py      # CRUD de reportes
├── seed_reportes.py     # Crea la colección e inserta 10 reportes de ejemplo
├── pyproject.toml       # Dependencias (Poetry)
├── poetry.lock
├── Dockerfile
└── .dockerignore
kubernetes/
├── mongo_statefulset.yaml        # MongoDB (StatefulSet + Service + Secret)
└── reports/
    └── backend_deployment.yaml   # ConfigMap, Secret, Service y Deployment del API
.github/workflows/
└── backend_build_image.yaml      # CI/CD: construye y publica la imagen en GHCR
```

## Configuración

El servicio lee su configuración de variables de entorno (en Kubernetes las inyectan un ConfigMap y un Secret; nada está escrito en el código):

| Variable           | Descripción                            | Ejemplo                                                      |
| ------------------ | -------------------------------------- | ------------------------------------------------------------ |
| `MONGO_URI`        | URI de conexión a MongoDB (Secret)     | `mongodb://admin:web3@mongo-service:27017/?authSource=admin` |
| `MONGO_DB`         | Nombre de la base de datos (ConfigMap) | `desarrollo_web_3`                                           |
| `MONGO_COLLECTION` | Colección del módulo (ConfigMap)       | `reportes_analitica`                                         |

## Levantar todo desde cero

### Requisitos

Docker, [Kind](https://kind.sigs.k8s.io/), `kubectl` y [Poetry](https://python-poetry.org/). Todos los comandos se ejecutan desde la **raíz del repositorio**, salvo que se indique lo contrario. Donde el comando cambia según la terminal, se muestran las versiones para **PowerShell (Windows)** y **bash (Linux/Mac)**.

### 1. Crear el cluster

```bash
kind create cluster --config kind-config.yaml --name web3
kubectl cluster-info --context kind-web3
kubectl get nodes
```

### 2. Crear el namespace

```bash
kubectl create namespace proyecto-final
```

### 3. Desplegar MongoDB

```bash
kubectl apply -f kubernetes/mongo_statefulset.yaml
kubectl get pods -n proyecto-final -w     # esperar a que mongo-0 esté en Running 1/1
```

### 4. Cargar los datos de ejemplo

En una terminal, abre un túnel hacia Mongo y déjalo abierto:

```bash
kubectl port-forward -n proyecto-final svc/mongo-service 27017:27017
```

En otra terminal, instala las dependencias y ejecuta el script:

**PowerShell (Windows)**

```powershell
cd backend/reports
poetry install --no-root
$env:MONGO_URI = "mongodb://admin:web3@localhost:27017/?authSource=admin"
$env:MONGO_DB = "desarrollo_web_3"
$env:MONGO_COLLECTION = "reportes_analitica"
poetry run python seed_reportes.py        # usa --reset para reiniciar la colección
```

**bash (Linux/Mac)**

```bash
cd backend/reports
poetry install --no-root
export MONGO_URI="mongodb://admin:web3@localhost:27017/?authSource=admin"
export MONGO_DB="desarrollo_web_3"
export MONGO_COLLECTION="reportes_analitica"
poetry run python seed_reportes.py        # usa --reset para reiniciar la colección
```

Debe imprimir que insertó 10 reportes. Las variables de entorno solo duran mientras la terminal esté abierta.

### 5. Desplegar el API

La imagen la construye y publica el pipeline de GitHub Actions (ver la sección de CI/CD); el Deployment la descarga de GHCR, no se construye a mano.

Antes de aplicar, verifica que el campo `image` de `kubernetes/reports/backend_deployment.yaml` apunte a la imagen publicada por el pipeline (todo en minúsculas):

```
ghcr.io/<usuario-u-organización>/<nombre-del-repo>:<rama>-latest
```

Si el paquete en GHCR es privado, hazlo público (GitHub → Packages → el paquete → _Package settings_ → _Change visibility_) para que el cluster pueda descargarlo.

```bash
kubectl apply -f kubernetes/reports/backend_deployment.yaml
kubectl get pods -n proyecto-final        # deben verse 2 pods del backend en Running
kubectl logs -n proyecto-final deploy/reportes-backend
```

Si el pipeline publica una versión nueva de la imagen:

```bash
kubectl rollout restart deployment/reportes-backend -n proyecto-final
```

### 6. Probar el API

```bash
kubectl port-forward -n proyecto-final svc/reportes-service 8000:8000
```

- Documentación interactiva: http://localhost:8000/docs (desde ahí se pueden probar todos los endpoints)
- Health check: http://localhost:8000/health
- Listar reportes: http://localhost:8000/reportes
  Crear un reporte:

**PowerShell (Windows)**

```powershell
$body = @{
  titulo = "Uso de laptops - Octubre"
  tipo = "uso_activos"
  periodo_inicio = "2026-10-01T00:00:00Z"
  periodo_fin = "2026-10-31T00:00:00Z"
  generado_por = "usuario.demo"
  metricas = @{ total_prestamos = 120; tasa_ocupacion = 0.7 }
} | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri http://localhost:8000/reportes -ContentType "application/json" -Body $body
```

**bash (Linux/Mac)**

```bash
curl -i -X POST http://localhost:8000/reportes \
  -H "Content-Type: application/json" \
  -d '{
    "titulo": "Uso de laptops - Octubre",
    "tipo": "uso_activos",
    "periodo_inicio": "2026-10-01T00:00:00Z",
    "periodo_fin": "2026-10-31T00:00:00Z",
    "generado_por": "usuario.demo",
    "metricas": {"total_prestamos": 120, "tasa_ocupacion": 0.7}
  }'
```

### 7. Verificar la persistencia

Elimina un pod del backend y el de Mongo, espera a que se recreen y vuelve a consultar `GET /reportes`: los datos siguen ahí gracias al volumen persistente del StatefulSet.

```bash
kubectl delete pod -n proyecto-final <nombre-del-pod-backend>
kubectl delete pod -n proyecto-final mongo-0
kubectl get pods -n proyecto-final -w
```

## Solución de problemas

| Síntoma                                                                          | Causa probable                                                                          | Solución                                                                                                |
| -------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------- |
| `Error: The current project could not be installed` al hacer `poetry install`    | Poetry intenta instalar la carpeta como paquete                                         | Usar `poetry install --no-root`                                                                         |
| `export` no se reconoce (PowerShell) / `KeyError: 'MONGO_URI'` al correr el seed | Las variables de entorno no se definieron                                               | En PowerShell usar `$env:NOMBRE = "valor"` en lugar de `export`                                         |
| El seed no conecta a Mongo                                                       | El `port-forward` no está activo                                                        | Mantener abierta la terminal con `kubectl port-forward ... mongo-service 27017:27017`                   |
| Pods en `InvalidImageName`                                                       | El campo `image` del Deployment tiene un valor inválido (mayúsculas o texto de relleno) | Poner el nombre real de la imagen, en minúsculas, y volver a aplicar el manifiesto                      |
| Pods en `ImagePullBackOff`                                                       | La imagen no existe o el paquete de GHCR es privado                                     | Revisar el nombre/tag y la visibilidad del paquete; `kubectl describe pod` muestra la causa en _Events_ |

## CI/CD

El workflow `.github/workflows/backend_build_image.yaml` se ejecuta con cada `push` a la rama del equipo. Construye la imagen desde `backend/reports` y la publica en el registro de contenedores de GitHub (GHCR) con dos tags:

- `<rama>-<número de ejecución>`: identifica cada versión.
- `<rama>-latest`: apunta a la última versión.
  El Deployment de Kubernetes usa la imagen publicada por este pipeline.

## Integrantes del equipo

| Integrante           | Aportación                                                                        |
| -------------------- | --------------------------------------------------------------------------------- |
| Christian Garcia     | Infraestructura: Dockerfile y manifiestos de Kubernetes                           |
| Daniel Salazar       | Base de la API: Poetry, configuración, conexión a MongoDB, `/health` y `/metrics` |
| Santiago Castellanos | Modelos Pydantic y utilidades                                                     |
| Julio Traconiz       | Endpoints CRUD                                                                    |
| Ruben Avalos         | Script de seed, workflow de CI/CD y documentación                                 |
