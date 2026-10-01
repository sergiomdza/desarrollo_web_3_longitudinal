#!/usr/bin/env bash
# Levanta (o actualiza) el stack de Categorías & Ubicaciones del Equipo 2
# en un cluster de kind, en el namespace "equipo-2".
set -euo pipefail

CLUSTER_NAME="web3"
NAMESPACE="equipo-2"
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "==> Verificando cluster de kind '${CLUSTER_NAME}'..."
if ! kind get clusters 2>/dev/null | grep -qx "${CLUSTER_NAME}"; then
  echo "==> No existe, creándolo con kind-config.yaml..."
  kind create cluster --name "${CLUSTER_NAME}" --config "${DIR}/kind-config.yaml"
else
  echo "==> Ya existe, se reutiliza."
fi

kubectl config use-context "kind-${CLUSTER_NAME}"

echo "==> Namespace..."
kubectl apply -f "${DIR}/namespace.yaml"

echo "==> Secret de MongoDB..."
kubectl apply -f "${DIR}/secret.yaml"

echo "==> StatefulSet + Service de MongoDB..."
kubectl apply -f "${DIR}/mongo_statefulset.yaml"

echo "==> Esperando a que mongo-0 esté listo..."
kubectl rollout status statefulset/mongo -n "${NAMESPACE}" --timeout=180s

echo "==> ConfigMap del backend..."
kubectl apply -f "${DIR}/backend_configmap.yaml"

echo "==> Deployment (2 réplicas) + Service del backend..."
kubectl apply -f "${DIR}/backend_deployment.yaml"

echo "==> Esperando a que el backend esté listo..."
kubectl rollout status deployment/backend -n "${NAMESPACE}" --timeout=180s

cat <<EOF

✅ Stack de Categorías & Ubicaciones arriba en el namespace '${NAMESPACE}'.

Para verlo en tu localhost:
  kubectl port-forward -n ${NAMESPACE} service/backend-service 8000:8000

Luego abre http://localhost:8000/docs

Nota: la imagen en GHCR hoy solo se publica para linux/amd64. Si tu máquina
es arm64 (Apple Silicon), antes de correr este script construye y precarga
la imagen local:
  cd ../../backend/products
  docker build -t ghcr.io/sergiomdza/categorias-ubicaciones:latest .
  kind load docker-image ghcr.io/sergiomdza/categorias-ubicaciones:latest --name ${CLUSTER_NAME}
EOF
