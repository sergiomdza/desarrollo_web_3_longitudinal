INTRUCCIONES GENERALES:

- MAIN estará reservado para entregas finales
- CADA equipo trabajando en su modulo tendrá su rama siguiendo esta nomenclatura: equipo\_#

```text
Estructura del proyecto:
/root
├── .github/
│   └── workflows/          # CI/CD Pipelines
├── kubernetes/
│   ├── ...                 # Common resources
│   └── equipo_#/
│       └── ...             # Deployment de la aplicación FastAPI
└── backend/
    └── equipo_#/
        ├── ...             # Código Python del backend
        ├── pyproject.toml  # Configuración y dependencias de Poetry
        ├── poetry.lock
        └── Dockerfile
```

> Nota: en la práctica, la carpeta de cada equipo dentro de `backend/` se
> nombra según el módulo que desarrolla. El Equipo 2 trabaja en
> `backend/products`, el microservicio de **Categorías & Ubicaciones**.

## Requisitos locales

- [Docker](https://www.docker.com/) (con el daemon corriendo)
- [Poetry](https://python-poetry.org/) >= 2.0
- Python >= 3.9 (el Dockerfile usa 3.12; en local puede variar)
- [kind](https://kind.sigs.k8s.io/) + `kubectl`, solo si vas a probar el stack de Categorías & Ubicaciones en Kubernetes
- [OpenLens](https://github.com/MuhammedKalkan/OpenLens) (opcional), para ver pods/deployments/servicios con una UI en vez de `kubectl`

## Primeros pasos tras clonar el repo

Para el servicio de **Categorías & Ubicaciones** (`backend/products`):

```bash
cd backend/products

# Instalar dependencias (usa el poetry.lock del repo, no lo regeneres sin avisar al equipo)
poetry install

# Correr las pruebas
poetry run pytest

# Levantar el servicio junto con MongoDB
docker compose up -d --build
```

Verifica que todo esté arriba:

```bash
curl http://localhost:8000/health
# {"status":"ok","database":"ok"}
```

La documentación interactiva de la API queda disponible en
http://localhost:8000/docs.

Para apagar todo:

```bash
docker compose down -v
```

> ⚠️ Si `poetry install` falla con un mensaje como _"pyproject.toml changed
> significantly since poetry.lock was last generated"_, es porque alguien
> modificó `pyproject.toml` sin correr `poetry lock` después. No lo
> regeneres por tu cuenta en una rama compartida sin avisar: el lock es un
> archivo del equipo y cambiarlo puede afectar a todos. Avisa en el canal del
> equipo y coordinen quién corre `poetry lock` y sube ese commit.

## Desplegar en Kubernetes (Equipo 2)

Los manifiestos de Categorías & Ubicaciones viven en `kubernetes/equipo_2/`:

| Archivo                   | Qué hace                                             |
| ------------------------- | ---------------------------------------------------- |
| `kind-config.yaml`        | Topología del cluster: 1 control-plane + 2 workers   |
| `namespace.yaml`          | Namespace `equipo-2`, donde vive todo lo demás       |
| `secret.yaml`             | Credenciales de Mongo + `MONGO_URI` completo         |
| `mongo_statefulset.yaml`  | StatefulSet de Mongo (1 réplica) + PVC 1Gi + Service |
| `backend_configmap.yaml`  | Nombre de la DB y de las 3 colecciones               |
| `backend_deployment.yaml` | Deployment del backend (**2 réplicas**) + Service    |
| `setup_app.sh`            | Aplica todo lo anterior en el orden correcto         |

```bash
cd kubernetes/equipo_2
./setup_app.sh
```

El script crea el cluster `web3` si no existe (usando `kind-config.yaml`), aplica
el namespace, el Secret, el StatefulSet de Mongo, el ConfigMap y el Deployment
del backend, y espera a que todo quede listo.

Para verlo en tu navegador:

```bash
kubectl port-forward -n equipo-2 service/backend-service 8000:8000
```

Luego abre http://localhost:8000/docs. En OpenLens: selecciona el contexto
`kind-web3`, filtra por el namespace `equipo-2` y entra a **Network →
Services → backend-service** para hacer el port-forward con un clic (ícono de
conector) en vez de usar la terminal.

> ⚠️ **Mac con Apple Silicon (arm64):** hoy la imagen publicada en GHCR
> (`ghcr.io/sergiomdza/categorias-ubicaciones:latest`) solo tiene build
> `linux/amd64`. Un `kubectl apply` directo va a dar `ImagePullBackOff` ahí.
> Antes de correr `setup_app.sh`, construye y precarga la imagen en local:
>
> ```bash
> cd backend/products
> docker build -t ghcr.io/sergiomdza/categorias-ubicaciones:latest .
> kind load docker-image ghcr.io/sergiomdza/categorias-ubicaciones:latest --name web3
> ```
>
> También puede pasar con `mongo:7.0` si el nodo donde cae el pod no la tiene
> cacheada (puede tardar en jalarla de internet). Si se traba en
> `ContainerCreating`, precárgala igual con
> `kind load docker-image mongo:7.0 --name web3`.

**Probar que los datos persisten** (StatefulSet con PVC + Deployment con 2
réplicas no deberían perder nada al reiniciar un pod):

```bash
# 1. Crea un activo de prueba
curl -X POST http://localhost:8000/activos -H 'Content-Type: application/json' -d '{
  "codigo":"TEST-001","nombre":"Prueba de persistencia",
  "categoria":{"nombre":"Infraestructura"},"ubicacion":{"nombre":"Rack 1","sede":"CDMX"},
  "estado":"disponible","valor_adquisicion":1}'

# 2. Borra mongo-0 y uno de los dos pods del backend (copia un nombre del
#    kubectl get pods de abajo)
kubectl get pods -n equipo-2
kubectl delete pod mongo-0 -n equipo-2
kubectl delete pod -n equipo-2 <nombre-de-un-pod-backend-...>

# 3. Espera a que se regeneren y vuelve a consultar: el activo debe seguir ahí
kubectl rollout status statefulset/mongo -n equipo-2
kubectl rollout status deployment/backend -n equipo-2
curl http://localhost:8000/activos
```

## CHEAT SHEET

-- DESCARGAR IMAGEN DE MONGO --

```bash
docker pull mongo:7.0
```

-- CADA QUE CAMBIEN EL CÓDIGO EN EL BACKEND TIENEN QUE CORRER ESTOS DOS --

- CREAR LA IMAGEN EN LOCAL (desde `backend/<modulo>`):

```bash
docker build -t <nombre-imagen> .
```

- SUBIRLA A LOS KIND NODES:

```bash
kind load docker-image <nombre-imagen>:latest --name web3
```

-- APLICAR EL DEPLOYMENT DE MONGO (compartido entre equipos) --

```bash
kubectl apply -f kubernetes/mongo_statefulset.yaml
```

-- CÓMO SABER SI EL CLUSTER DE KIND ESTÁ VIVO --

```bash
kubectl cluster-info --context kind-web3
kubectl get nodes
```

-- CREAR CLUSTER DE KIND --

```bash
kind create cluster --name web3
```

> El Equipo 2 ya tiene su `kind-config.yaml` y sus manifiestos de
> `Deployment`/`Service` completos en `kubernetes/equipo_2/` (ver sección
> [Desplegar en Kubernetes](#desplegar-en-kubernetes-equipo-2) arriba). El
> stack de observabilidad (Prometheus/Grafana) todavía no existe en ningún
> módulo. Si tu equipo necesita sus propios manifiestos, sigue el mismo
> patrón: una carpeta `kubernetes/<modulo>/` con su propio namespace, Secret,
> ConfigMap, Deployment/StatefulSet, Service y un `setup_app.sh`.

## Estado por módulo

| Módulo                              | Carpeta                 | README                                                             | Kubernetes                |
| ----------------------------------- | ----------------------- | ------------------------------------------------------------------ | ------------------------- |
| Categorías & Ubicaciones (Equipo 2) | `backend/products`      | [backend/products/README.md](backend/products/README.md)           | ✅ `kubernetes/equipo_2/` |
| Auditorías                          | `backend/audits`        | [backend/audits/README.md](backend/audits/README.md)               | —                         |
| Notificaciones                      | `backend/notifications` | [backend/notifications/README.md](backend/notifications/README.md) | —                         |
| Reportes                            | `backend/reports`       | [backend/reports/README.md](backend/reports/README.md)             | —                         |
| Solicitudes                         | `backend/requests`      | [backend/requests/README.md](backend/requests/README.md)           | —                         |
| Usuarios                            | `backend/users`         | [backend/users/README.md](backend/users/README.md)                 | —                         |
