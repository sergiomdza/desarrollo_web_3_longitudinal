# Módulo de Auditorías

## Descripción

Este módulo implementa una API REST para la administración de auditorías utilizando FastAPI y MongoDB.

La entidad principal es `Auditoria`, la cual permite registrar información relacionada con una auditoría mediante los siguientes campos:

- `id`: identificador único de la auditoría.
- `nombre`: nombre o descripción de la auditoría.
- `usuario`: usuario relacionado con la auditoría.
- `fecha`: fecha y hora de la auditoría.

El módulo cuenta con operaciones CRUD, validación de datos mediante Pydantic, conexión a MongoDB mediante variables de entorno, endpoint de salud y métricas para Prometheus.

---

## Endpoints

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/` | Comprueba que la API de Auditorías está funcionando |
| GET | `/health` | Comprueba el estado del servicio |
| GET | `/metrics` | Expone métricas para Prometheus |
| GET | `/auditorias` | Obtiene todas las auditorías |
| GET | `/auditorias/{id}` | Obtiene una auditoría por su ID |
| POST | `/auditorias` | Crea una nueva auditoría |
| PUT | `/auditorias/{id}` | Actualiza una auditoría existente |
| DELETE | `/auditorias/{id}` | Elimina una auditoría |

---

## Estructura del módulo

```text
backend/audits/
├── app/
│   ├── __init__.py
│   ├── database.py
│   ├── main.py
│   └── models.py
├── .dockerignore
├── .gitignore
├── crear_auditorias.sh
├── Dockerfile
├── poetry.lock
├── pyproject.toml
└── README.md
```

---

## CI/CD

El workflow [`.github/workflows/cicd_equipo_1_audits.yaml`](../../.github/workflows/cicd_equipo_1_audits.yaml) se ejecuta en cada push a la rama `equipo_1`. Construye la imagen a partir de este directorio y la publica en GitHub Container Registry:

```text
ghcr.io/sergiomdza/desarrollo_web_3_longitudinal-audits
```

Cada imagen se publica con dos tags:

| Tag | Ejemplo | Uso |
|---|---|---|
| `equipo_1-<run>` | `equipo_1-12` | Identifica la versión: número de ejecución del pipeline en GitHub Actions |
| `equipo_1-latest` | `equipo_1-latest` | Última versión publicada; la usa el Deployment |

La imagen también lleva los labels OCI `org.opencontainers.image.revision` (commit) y `org.opencontainers.image.source` (repositorio).

### Despliegue en Kubernetes

El Deployment de [`kubernetes/audits/backend_deployment.yaml`](../../kubernetes/audits/backend_deployment.yaml) usa la imagen publicada por el pipeline con `imagePullPolicy: Always`, por lo que ya no es necesario construir la imagen a mano ni cargarla con `kind load`.

```bash
kubectl apply -f kubernetes/audits/backend_deployment.yaml

# Después de que el pipeline publique una nueva imagen:
kubectl rollout restart deployment/audits-api -n proyecto-final
```

Para fijar o regresar a una versión concreta:

```bash
kubectl set image deployment/audits-api -n proyecto-final \
  audits-api=ghcr.io/sergiomdza/desarrollo_web_3_longitudinal-audits:equipo_1-<run>
```

Para ver qué versión está corriendo:

```bash
kubectl get pods -n proyecto-final -l app=audits-api \
  -o jsonpath='{range .items[*]}{.status.containerStatuses[0].imageID}{"\n"}{end}'
```

Si los pods quedan en `ImagePullBackOff`, el paquete en GHCR no es público: el dueño del repositorio debe cambiar su visibilidad a *Public* en **Packages → desarrollo_web_3_longitudinal-audits → Package settings**.