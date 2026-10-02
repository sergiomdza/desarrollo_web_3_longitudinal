#!/usr/bin/env bash

set -euo pipefail

CLUSTER_NAME="web3"
NAMESPACE="proyecto-final"

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "======================================"
echo " Equipo 4 - Préstamos / Solicitudes"
echo " Kubernetes + Kind"
echo "======================================"

echo ""
echo "==> Verificando Kind..."

if ! kind get clusters 2>/dev/null | grep -qx "${CLUSTER_NAME}"; then

    echo "==> Creando cluster ${CLUSTER_NAME}..."

    kind create cluster \
        --name "${CLUSTER_NAME}" \
        --config "${DIR}/kind-config.yaml"

else

    echo "==> El cluster ${CLUSTER_NAME} ya existe."

fi


echo ""
echo "==> Seleccionando contexto..."

kubectl config use-context "kind-${CLUSTER_NAME}"


echo ""
echo "==> Creando namespace..."

kubectl apply \
    -f "${DIR}/namespace.yaml"


echo ""
echo "==> Creando Secret..."

kubectl apply \
    -f "${DIR}/secret.yaml"


echo ""
echo "==> Creando ConfigMap..."

kubectl apply \
    -f "${DIR}/backend_configmap.yaml"


echo ""
echo "==> Desplegando MongoDB..."

kubectl apply \
    -f "${DIR}/mongo_statefulset.yaml"


echo ""
echo "==> Esperando MongoDB..."

kubectl rollout status \
    statefulset/mongo \
    -n "${NAMESPACE}" \
    --timeout=180s


echo ""
echo "==> Desplegando API..."

kubectl apply \
    -f "${DIR}/backend_deployment.yaml"


echo ""
echo "==> Esperando API..."

kubectl rollout status \
    deployment/backend-requests \
    -n "${NAMESPACE}" \
    --timeout=180s


echo ""
echo "======================================"
echo " Kubernetes listo"
echo "======================================"

echo ""
echo "Pods:"
kubectl get pods -n "${NAMESPACE}"

echo ""
echo "Services:"
kubectl get services -n "${NAMESPACE}"

echo ""
echo "StatefulSets:"
kubectl get statefulsets -n "${NAMESPACE}"

echo ""
echo "Deployments:"
kubectl get deployments -n "${NAMESPACE}"

echo ""
echo "Para acceder a FastAPI:"
echo ""
echo "kubectl port-forward -n ${NAMESPACE} service/backend-requests-service 8000:8000"
echo ""
echo "Swagger:"
echo "http://localhost:8000/docs"