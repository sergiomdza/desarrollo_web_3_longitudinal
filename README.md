INTRUCCIONES GENERALES:
- MAIN estará reservado para entregas finales
- CADA equipo trabajando en su modulo tendrá su rama siguiendo esta nomenclatura: equipo_# 

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


CHEAT SHEET: 

-- DESCARGAR IMAGENES --
docker pull mongo:7.0


-- CADA QUE CAMBIEN EL CÓDIGO EN EL BACKEND TIENE QUE CORRER ESTOS DOS: -- 

- CREAR LA IMAGEN EN LOCAL:
docker build -t backend_productos .

- ⁠SUBIRLA A LOS KIND NODES:
kind load docker-image backend_productos:latest --name web3

-- Aplicar nuestro deployment del backend -- 
kubectl apply -f backend_deployment.yaml

-- Aplicar nuestro deployment de mongo -- 
kubectl apply -f mongo_statefulset.yaml

-- SUBIR IMAGENES AL KIND NODE --
kind load docker-image backend_productos:latest --name web3

-- EXPORTAR E IMPORTAR IMAGENES DE MONGO -- 
--- Importar --- 
docker save -o kind-node.tar kindest/node

--- Exportar --- 
docker import kind-node.tar kindest/node

-- COMO SABER SI MI KUBERNTES CLUSTER DE KIND ESTÁ VIVO -- 
kubectl cluster-info --context kind-web3
kubectl get nodes

-- CREAR CLUSTER DE KIND --
kind create cluster --config kind-config.yaml --name web3

-- OBSERVABILIDAD --

El backend expone las métricas de Prometheus en `GET /metrics`. Para desplegar
Prometheus y Grafana junto con MongoDB y el backend:

```bash
cd Kubernetes
./setup_app.sh
```

Para acceder desde la máquina local:

```bash
kubectl port-forward service/prometheus 9090:9090
kubectl port-forward service/grafana 3000:3000
```

Prometheus estará en http://localhost:9090 y Grafana en http://localhost:3000.
Las credenciales iniciales de Grafana son `admin` / `admin`. En Prometheus se
puede comprobar el objetivo en **Status > Target health**; debe aparecer
`backend-service.default.svc.cluster.local:8000` como `UP`.
