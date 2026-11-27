#!/usr/bin/env bash
# Conecta Categorías & Ubicaciones (namespace proyecto-final) con el
# Prometheus y el Alloy compartidos del stack de clase (namespace default).
#
# Requisitos:
#   - El stack de clase corriendo en default (Prometheus, Grafana, Loki, Alloy).
#   - El módulo desplegado con ../setup_app.sh.
set -euo pipefail

CLUSTER_NAME="web3"
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

kubectl config use-context "kind-${CLUSTER_NAME}"

echo "==> Verificando el stack de clase en 'default'..."
for deploy in prometheus alloy; do
  if ! kubectl get "deployment/${deploy}" -n default >/dev/null 2>&1; then
    echo "❌ No existe deployment/${deploy} en 'default'."
    echo "   Apliquen primero monitoring_tools.yaml y logging.yaml del profesor."
    exit 1
  fi
done

echo "==> Service headless de métricas (proyecto-final)..."
kubectl apply -f "${DIR}/metrics_service.yaml"

echo "==> Permisos de Alloy para leer logs en proyecto-final..."
kubectl apply -f "${DIR}/alloy_rbac.yaml"

echo "==> ConfigMaps de Prometheus y Alloy (default)..."
kubectl apply -f "${DIR}/prometheus_config.yaml"
kubectl apply -f "${DIR}/alloy_config.yaml"

echo "==> Reiniciando Prometheus y Alloy para que lean la nueva configuración..."
kubectl rollout restart deployment/prometheus -n default
kubectl rollout restart deployment/alloy -n default
kubectl rollout status deployment/prometheus -n default --timeout=180s
kubectl rollout status deployment/alloy -n default --timeout=180s

cat <<MSG

✅ Observabilidad conectada.

Pods que encuentra el Service headless (deben ser 2):
$(kubectl get endpointslices -n proyecto-final -l kubernetes.io/service-name=categorias-ubicaciones-metrics \
    -o jsonpath='{range .items[*].endpoints[*]}  {.addresses[0]}{"\n"}{end}')

Para verificar:
  Prometheus:  kubectl port-forward -n default service/prometheus-service 9090:9090
               -> http://localhost:9090/targets  (job categorias-ubicaciones, 2 en UP)
  Grafana:     kubectl port-forward -n default service/grafana-service 3000:3000
               -> Explore -> Loki -> {app="categorias-ubicaciones"}
MSG
