#!/usr/bin/env bash
# Levanta (o actualiza) el stack de Categorías & Ubicaciones del Equipo 2
# en un cluster de kind, en el namespace compartido "proyecto-final".
set -euo pipefail

CLUSTER_NAME="web3"
NAMESPACE="proyecto-final"
DEPLOYMENT="categorias-ubicaciones-api"
SERVICE="categorias-ubicaciones-service"
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "==> Verificando cluster de kind '${CLUSTER_NAME}'..."
if ! kind get clusters 2>/dev/null | grep -qx "${CLUSTER_NAME}"; then
  echo "==> No existe, creándolo con kind-config.yaml..."
  kind create cluster --name "${CLUSTER_NAME}" --config "${DIR}/kind-config.yaml"
else
  echo "==> Ya existe, se reutiliza."
fi

kubectl config use-context "kind-${CLUSTER_NAME}"

echo "==> Namespace ${NAMESPACE}..."
kubectl apply -f "${DIR}/namespace.yaml"

echo "==> MongoDB común (StatefulSet + PVC + Service + Secret)..."
kubectl apply -f "${DIR}/../mongo_statefulset.yaml"

echo "==> Esperando a que mongo-0 esté listo..."
kubectl rollout status statefulset/mongo -n "${NAMESPACE}" --timeout=180s

echo "==> Secret y ConfigMap del backend..."
kubectl apply -f "${DIR}/secret.yaml"
kubectl apply -f "${DIR}/backend_configmap.yaml"

echo "==> Deployment (2 réplicas) + Service del backend..."
kubectl apply -f "${DIR}/backend_deployment.yaml"

echo "==> Esperando a que el backend esté listo..."
kubectl rollout status "deployment/${DEPLOYMENT}" -n "${NAMESPACE}" --timeout=180s

cat <<MSG

✅ Stack de Categorías & Ubicaciones arriba en el namespace '${NAMESPACE}'.

Para verlo en tu localhost:
  kubectl port-forward -n ${NAMESPACE} service/${SERVICE} 8000:8000

Luego abre http://localhost:8000/docs
MSG
