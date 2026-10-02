# Equipo #6 — Notificaciones

Recordatorios de devolución, alertas de vencimiento y confirmaciones de
aprobación. El servicio **reacciona a los eventos del módulo de Préstamos**
(Equipo #4) y guarda las notificaciones en la colección `notificaciones`.

## Levantar en local

Requisitos: Docker Desktop.

```bash
cd backend/notifications
docker compose up --build -d                       # MongoDB + API
docker compose run --rm api python scripts/seeder.py   # datos de ejemplo (opcional)
```

- API: http://localhost:8000
- Swagger: http://localhost:8000/docs
- MongoDB: `mongodb://admin:web3@localhost:27017/?authSource=admin` (BD `proyecto_final`)

Para detener: `docker compose down` (agrega `-v` para borrar los datos).

### Sin Docker para la API (sólo Mongo en Docker)

```bash
docker compose up -d mongo
poetry install
cp .env.example .env    # y exporta las variables
poetry run uvicorn app.main:app --reload
```

### Pruebas

```bash
poetry run pytest
```

### Colección de Postman

`postman/notificaciones.postman_collection.json` (23 requests, 44 asserts):
health, CRUD completo con casos de error y el flujo de eventos de Préstamos.
Importarla en Postman y usar **Run collection** en orden. La variable
`baseUrl` es `http://localhost:8000` (Compose) o `http://localhost:8001` (kind).

Desde terminal: `npx newman run postman/notificaciones.postman_collection.json`

## Kubernetes (kind)

Manifiestos en `kubernetes/notifications/` (ConfigMap, Secret, Deployment con
2 réplicas y probes en `/health`, Service `notificaciones:80`). Requieren el
`mongo-service` de `kubernetes/mongo_statefulset.yaml`.

```bash
# desde la raíz del repo
kind create cluster --name web3
kubectl create namespace proyecto-final
kubectl apply -f kubernetes/mongo_statefulset.yaml

docker build -t notificaciones:local backend/notifications
kind load docker-image notificaciones:local --name web3

kubectl apply -f kubernetes/notifications/
kubectl -n proyecto-final port-forward svc/notificaciones 8001:80
```

Cada vez que cambie el código: `docker build` + `kind load` +
`kubectl -n proyecto-final rollout restart deployment/notificaciones`.

Seeder dentro del cluster:
`kubectl -n proyecto-final exec deploy/notificaciones -- python scripts/seeder.py`

## CI/CD

`.github/workflows/cicd_equipo_6_notifications.yaml`:

- **test**: en cada push a `equipo_6` / `equipo_6_*` y en PRs que toquen
  `backend/notifications/**` — instala con Poetry y corre `pytest`.
- **build-and-push-image**: sólo en push a `equipo_6`, si las pruebas pasan.
  Publica en GHCR `…-notifications:equipo_6-<run>` y `:equipo_6-latest`
  (para usarla en el cluster, cambiar `image:` en
  `kubernetes/notifications/deployment.yaml`).

## Contrato con Préstamos

Préstamos llama a `POST /eventos/prestamos` cada vez que cambia el estado de un
préstamo:

```json
{
  "evento": "prestamo_aprobado",
  "prestamo_id": "PREST-100",
  "usuario_id": "USR-100",
  "activo_nombre": "Proyector Epson",
  "fecha_devolucion": "2026-10-08T12:00:00Z",
  "motivo": null,
  "canal": "in_app"
}
```

| `evento`              | Notificaciones que se generan                                                    |
|-----------------------|----------------------------------------------------------------------------------|
| `prestamo_aprobado`   | `confirmacion_aprobacion` (enviada) + `recordatorio_devolucion` programado 1 día antes de `fecha_devolucion` |
| `prestamo_rechazado`  | `confirmacion_rechazo` con el `motivo`                                            |
| `prestamo_por_vencer` | `alerta_vencimiento`                                                             |
| `prestamo_vencido`    | `alerta_vencimiento` y cancela el recordatorio pendiente                         |
| `prestamo_devuelto`   | `notificacion_general` de confirmación y cancela recordatorios/alertas pendientes |

El evento es **idempotente**: el `codigo` de cada notificación es
`<PREFIJO>-<prestamo_id>` (`APR`, `REC`, `RCH`, `PVN`, `VEN`, `DEV`), así que si
Préstamos reintenta la llamada no se duplica nada.

## Endpoints

| Método | Ruta                                  | Descripción                                             |
|--------|---------------------------------------|---------------------------------------------------------|
| GET    | `/health`                             | Estado de la API y MongoDB                              |
| POST   | `/eventos/prestamos`                  | Reaccionar a un evento de Préstamos                     |
| POST   | `/notificaciones`                     | Crear notificación manual                               |
| GET    | `/notificaciones`                     | Listar (filtros: `tipo`, `estado`, `destinatario_id`, `prestamo_id`, `skip`, `limit`) |
| GET    | `/notificaciones/{id}`                | Obtener por ID                                          |
| PUT    | `/notificaciones/{id}`                | Actualizar                                              |
| PATCH  | `/notificaciones/{id}/leida`          | Marcar como leída                                       |
| DELETE | `/notificaciones/{id}`                | Eliminar                                                |
| POST   | `/notificaciones/despachar`           | Envía las `pendiente` cuya `fecha_programada` ya pasó   |

Estados: `pendiente`, `enviada`, `leida`, `fallida`, `cancelada`.
Todavía no hay proveedor real de email/push: "despachar" marca la notificación
como `enviada`.
