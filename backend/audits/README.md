Equipo #1


## 1. Levantar MongoDB en Kubernetes

Desde la raíz del repositorio, crear el namespace:

```bash
kubectl create namespace proyecto-final
```

> Si el namespace ya existe, no es necesario volver a crearlo.

Aplicar el archivo de MongoDB:

```bash
kubectl apply -f ./kubernetes/mongo_statefulset.yaml
```

Verificar que MongoDB esté corriendo:

```bash
kubectl get pods -n proyecto-final
```

Verificar el servicio:

```bash
kubectl get svc -n proyecto-final
```

---

## 2. Conectarse a MongoDB desde local

Abrir el puerto de MongoDB:

Hacer un port-forward del servicio de mongo al puerto 27017 (Si no deja cambiar el de la clase a 27019)

### MongoDB Compass

Usar la siguiente URI:

```text
mongodb://admin:web3@localhost:27017/?authSource=admin
```

Credenciales:

```text
Usuario: admin
Contraseña: web3
```

---

## 3. Entrar al módulo de Auditorías

Desde la raíz del repositorio:

```bash
cd backend/audits
```

La estructura principal es:

```text
backend/
└── audits/
    ├── app/
    │   ├── __init__.py
    │   ├── main.py
    │   ├── database.py
    │   └── models.py
    ├── crear_auditorias.sh
    ├── README.md
    ├── pyproject.toml
    └── poetry.lock
```

---

## 4. Generar la colección y datos iniciales

Desde `backend/audits` ejecutar:

```bash
bash crear_auditorias.sh
```

Este script crea la colección `auditorias` e inserta los datos iniciales.

---

## 5. Instalar las dependencias

Desde `backend/audits`:

```bash
poetry install
```

Las dependencias se encuentran definidas en `pyproject.toml` y `poetry.lock`.

---

## 6. Configurar variables de entorno

Crear un archivo `.env` dentro de `backend/audits`:

Agregar:

```env
MONGO_URI=mongodb://admin:web3@localhost:27017/?authSource=admin
MONGO_DB=DB_Proyecto
MONGO_COLLECTION=auditorias
```

El archivo `.env` no debe subirse al repositorio.

---

## 7. Ejecutar la API localmente

Desde `backend/audits`:

```bash
poetry run uvicorn app.main:app --reload --port 8001
``