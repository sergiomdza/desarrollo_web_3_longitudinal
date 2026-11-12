# Módulo de Auditorías

## Descripción

El módulo de **Auditoría y Cumplimiento** implementa una API REST desarrollada con **FastAPI** y **MongoDB** para administrar una bitácora de acciones realizadas en el sistema.

La entidad principal es `Auditoria`, compuesta por los siguientes campos:

- `id`: identificador único de la auditoría.
- `nombre`: nombre o descripción de la acción registrada.
- `usuario`: usuario relacionado con la acción.
- `fecha`: fecha y hora en que se realizó.

El módulo permite realizar operaciones CRUD sobre las auditorías, valida los datos mediante Pydantic y utiliza variables de entorno para la configuración de MongoDB.

---

## Endpoints

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/` | Comprueba que la API está funcionando |
| GET | `/health` | Comprueba el estado del servicio |
| GET | `/metrics` | Expone las métricas para Prometheus |
| GET | `/auditorias` | Obtiene todas las auditorías |
| GET | `/auditorias/{id}` | Obtiene una auditoría por ID |
| POST | `/auditorias` | Crea una nueva auditoría |
| PUT | `/auditorias/{id}` | Actualiza los campos de una auditoría |
| DELETE | `/auditorias/{id}` | Elimina una auditoría |

La documentación interactiva de la API está disponible en `/docs`.

---

## Levantar el proyecto desde cero

### 1. Crear el namespace

```bash
kubectl create namespace proyecto-final
```

Si el namespace ya existe, este paso puede omitirse.

### 2. Levantar MongoDB

Desde la raíz del repositorio:

```bash
kubectl apply -f kubernetes/audits/mongo_statefulset.yaml
```

Verificar que MongoDB esté corriendo:

```bash
kubectl get pods -n proyecto-final
```

Debe aparecer el pod:

```text
mongo-0
```

con estado `Running`.

### 3. Crear la colección de auditorías

Entrar a la carpeta del módulo:

```bash
cd backend/audits
```

Ejecutar el script:

```bash
bash crear_auditorias.sh
```

El script crea la colección `auditorias` en `DB_Proyecto` e inserta los registros iniciales.

Regresar a la raíz del repositorio:

```bash
cd ../..
```

### 4. Desplegar la API

La imagen Docker de la API es generada y publicada automáticamente en GitHub Container Registry mediante GitHub Actions.

Aplicar el manifiesto:

```bash
kubectl apply -f kubernetes/audits/backend_deployment.yaml
```

Verificar los pods:

```bash
kubectl get pods -n proyecto-final
```

Deben aparecer dos réplicas de `audits-api` y el pod de MongoDB con estado `Running`:

```text
audits-api-xxxxxxxxxx-xxxxx    Running
audits-api-xxxxxxxxxx-xxxxx    Running
mongo-0                        Running
```

También se pueden verificar el Deployment y Service:

```bash
kubectl get deployments -n proyecto-final
kubectl get services -n proyecto-final
```

### 5. Probar la API

Realizar un port-forward del servicio:

```bash
kubectl port-forward -n proyecto-final svc/audits-service 8001:8001
```

Mientras el comando permanezca ejecutándose, la API estará disponible en:

```text
http://localhost:8001
```

Comprobar el estado:

```text
http://localhost:8001/health
```

Documentación Swagger:

```text
http://localhost:8001/docs
```

Desde `/docs` se pueden probar todos los endpoints CRUD.

### 6. Ver los logs

Para obtener los pods de la API:

```bash
kubectl get pods -n proyecto-final -l app=audits-api
```

Para consultar los logs:

```bash
kubectl logs -n proyecto-final <nombre-del-pod>
```

---

## CI/CD

El workflow:

```text
.github/workflows/cicd_equipo_1_audits.yaml
```

se ejecuta automáticamente al realizar un push a la rama `equipo_1`.

El pipeline construye la imagen Docker del módulo y la publica en GitHub Container Registry:

```text
ghcr.io/sergiomdza/desarrollo_web_3_longitudinal-audits
```

Las imágenes utilizan los tags:

```text
equipo_1-<run>
equipo_1-latest
```

El Deployment utiliza `equipo_1-latest` con:

```yaml
imagePullPolicy: Always
```

por lo que Kubernetes obtiene la imagen publicada en GHCR.

Cuando se publique una nueva versión, se puede reiniciar el Deployment con:

```bash
kubectl rollout restart deployment/audits-api -n proyecto-final
```

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

kubernetes/audits/
├── backend_deployment.yaml
└── mongo_statefulset.yaml

.github/workflows/
└── cicd_equipo_1_audits.yaml
```

---

## Integrantes del equipo

**Equipo 1**

- Eliam Matus Salvador
- Kevin Emanuel Garabita Córdova
- Juan Felipe Cervantes Alonzo
- Emiliano Martinez Ramon
- Juan Ramon Ake Canul