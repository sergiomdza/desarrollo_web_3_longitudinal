# Modulo de Notificaciones

## Descripcion

El modulo de notificaciones se encarga de gestionar notificaciones relacionadas con los prestamos de activos institucionales.

Entre las notificaciones contempladas se encuentran:

- Recordatorios de devolucion
- Alertas de vencimiento
- Confirmaciones de aprobacion
- Confirmaciones de rechazo
- Notificaciones generales

La entidad principal implementada es 'Notificacion'.

Cada notificacion puede contener informacion como el codigo de la notificacion, tipo, canal de envío, destinatario, préstamo relacionado, título, mensaje, estado y fechas relacionadas con su programacion y su lectura.

## Endpoints

| Metodo | Ruta                 | Descripcion                                                               |
| ------ | -------------------- | ------------------------------------------------------------------------- |
| GET    | /health              | Verifica que el servicio este activo y haya conexion con la base de datos |
| POST   | /notificaciones      | Crea una nueva notificacion                                               |
| GET    | /notificaciones      | Obtiene la lista de notificaciones                                        |
| GET    | /notificaciones/{id} | Obtiene una notificacion por ID                                           |
| PUT    | /notificaciones/{id} | Actualiza una notificacion                                                |
| DELETE | /notificaciones/{id} | Elimina una notificacion                                                  |

## Instrucciones

### 1. Crear el cluster de Kubernetes

- Correr Docker Desktop

- kind create cluster --name desarrollo-web

kubectl config current-context

kubectl get nodes

### 2. Crear el namespace

kubectl create namespace proyecto-final

### 3. Aplicar MongoDB

kubectl apply -f kubernetes/mongo_statefulset.yaml

kubectl get pods -n proyecto-final

### 4. Aplicar los manifiestos de Notificaciones

kubectl apply -f kubernetes/notifications/

kubectl get pods -n proyecto-final

kubectl get svc -n proyecto-final

### 5. Probar el API

kubectl port-forward -n proyecto-final svc/notificaciones 8000:80

Invoke-RestMethod -Method Get -Uri "http://localhost:8000/health"

## Integrantes del equipo

- Victor Becerra
- Andres Saldana
- Maria Alejandra Kantun
- Gabriel Kuuk
