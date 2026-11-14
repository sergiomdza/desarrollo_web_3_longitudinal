#!/usr/bin/env bash
# =============================================================================
# Levanta las métricas del módulo de Auditorías en el cluster local de Kind
# y carga el dashboard de Grafana.
#
# Uso (desde la raíz del repositorio):
#   bash kubernetes/audits/levantar_metricas_audits.sh
#
# Qué hace:
#   1. Construye la imagen de audits con el código local y la carga en Kind
#      (el CI solo publica imagen al hacer push a equipo_1).
#   2. Actualiza el Deployment audits-api para usar esa imagen.
#   3. Aplica monitoring_tools.yaml (Prometheus + Grafana) en proyecto-final
#      y reinicia ambos para que tomen la configuración nueva.
#   4. Importa el dashboard kubernetes/audits/grafana/audits-dashboard.json.
#   5. Genera tráfico de prueba para que los paneles tengan datos.
# =============================================================================
set -euo pipefail

NS="proyecto-final"
IMAGE="audits-api:local"
REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
DASHBOARD="$REPO_ROOT/kubernetes/audits/grafana/audits-dashboard.json"
GRAFANA_USER="grafana_admin"
GRAFANA_PASS="web3"
PF_PIDS=()

cleanup() { for p in "${PF_PIDS[@]:-}"; do kill "$p" 2>/dev/null || true; done; }
trap cleanup EXIT

paso() { printf '\n\033[1;34m==> %s\033[0m\n' "$*"; }

# --- 0. Verificaciones -------------------------------------------------------
paso "Verificando herramientas y cluster"
for cmd in docker kind kubectl curl; do
  command -v "$cmd" >/dev/null || { echo "Falta '$cmd' en el PATH"; exit 1; }
done
docker info >/dev/null 2>&1 || { echo "Docker no está corriendo. Abre Docker Desktop y vuelve a intentar."; exit 1; }
CLUSTER="$(kind get clusters | head -n1)"
[ -n "$CLUSTER" ] || { echo "No hay cluster de Kind. Créalo con: kind create cluster"; exit 1; }
echo "Cluster Kind: $CLUSTER"
kubectl get namespace "$NS" >/dev/null || { echo "No existe el namespace $NS (ver backend/audits/README.md)"; exit 1; }
kubectl -n "$NS" get deployment audits-api >/dev/null || {
  echo "No existe audits-api; aplicando kubernetes/audits/backend_deployment.yaml"
  kubectl apply -f "$REPO_ROOT/kubernetes/audits/backend_deployment.yaml"
}

# --- 1. Imagen local ---------------------------------------------------------
paso "Construyendo imagen $IMAGE"
docker build -t "$IMAGE" "$REPO_ROOT/backend/audits"
paso "Cargando imagen en Kind"
kind load docker-image "$IMAGE" --name "$CLUSTER"

# --- 2. Deployment de audits -------------------------------------------------
paso "Actualizando Deployment audits-api"
kubectl -n "$NS" patch deployment audits-api --type=json -p='[
  {"op":"replace","path":"/spec/template/spec/containers/0/image","value":"'"$IMAGE"'"},
  {"op":"replace","path":"/spec/template/spec/containers/0/imagePullPolicy","value":"IfNotPresent"}
]'
# Prometheus scrapea a través del Service: con 2 réplicas cada scrape cae en un
# pod distinto y los contadores "brincan". Para la demo se deja 1 réplica.
kubectl -n "$NS" scale deployment audits-api --replicas=1
# La imagen conserva el tag audits-api:local; se reinicia para que tome la nueva.
kubectl -n "$NS" rollout restart deployment audits-api
kubectl -n "$NS" rollout status deployment audits-api --timeout=180s

# --- 3. Prometheus + Grafana ---------------------------------------------------
paso "Aplicando Prometheus y Grafana en $NS"
kubectl apply -f "$REPO_ROOT/kubernetes/monitoring_tools.yaml" -n "$NS"
kubectl -n "$NS" rollout restart deployment prometheus grafana
kubectl -n "$NS" rollout status deployment prometheus --timeout=180s
kubectl -n "$NS" rollout status deployment grafana --timeout=180s

# --- 4. Port-forwards ----------------------------------------------------------
paso "Abriendo port-forwards (temporales)"
kubectl -n "$NS" port-forward svc/grafana-service 3000:3000 >/dev/null 2>&1 & PF_PIDS+=($!)
kubectl -n "$NS" port-forward svc/audits-service 8001:8001 >/dev/null 2>&1 & PF_PIDS+=($!)
for i in $(seq 1 30); do
  curl -s -o /dev/null http://localhost:3000/api/health && curl -s -o /dev/null http://localhost:8001/health && break
  sleep 1
done

# --- 5. Dashboard --------------------------------------------------------------
paso "Importando dashboard en Grafana"
printf '{"dashboard": %s, "overwrite": true}' "$(cat "$DASHBOARD")" \
  | curl -sS -u "$GRAFANA_USER:$GRAFANA_PASS" -H 'Content-Type: application/json' \
      -X POST http://localhost:3000/api/dashboards/db --data-binary @-
echo

# --- 6. Tráfico de prueba --------------------------------------------------------
paso "Generando tráfico de prueba (~1 minuto)"
API=http://localhost:8001
for ronda in $(seq 1 30); do
  id=$((900000 + RANDOM))
  curl -s -o /dev/null -X POST "$API/auditorias" -H 'Content-Type: application/json' \
    -d '{"id":'"$id"',"nombre":"Prueba metricas","usuario":"juan.cervantes","fecha":"2026-11-13T10:00:00"}'
  curl -s -o /dev/null "$API/auditorias"
  curl -s -o /dev/null "$API/auditorias/$id"
  curl -s -o /dev/null -X PUT "$API/auditorias/$id" -H 'Content-Type: application/json' -d '{"nombre":"Editada"}'
  curl -s -o /dev/null "$API/auditorias/999999999"                      # 404
  curl -s -o /dev/null -X POST "$API/auditorias" -H 'Content-Type: application/json' -d '{"id":"x"}'  # 422
  curl -s -o /dev/null -X DELETE "$API/auditorias/$id"
  sleep 2
done

paso "Listo"
cat <<EOF
- Prometheus (Targets):  kubectl -n $NS port-forward svc/prometheus-service 9090:9090
                         -> http://localhost:9090/targets  (job "auditorias" en UP)
- Grafana:               kubectl -n $NS port-forward svc/grafana-service 3000:3000
                         -> http://localhost:3000/d/audits-api  (usuario $GRAFANA_USER / $GRAFANA_PASS)
EOF
