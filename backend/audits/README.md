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