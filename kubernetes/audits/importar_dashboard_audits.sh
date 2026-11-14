#!/usr/bin/env bash
# =============================================================================
# Importa el dashboard de Auditorías en Grafana y genera tráfico de prueba.
# (Pasos 4-6 de levantar_metricas_audits.sh; se puede correr por separado.)
#
# Uso (desde la raíz del repositorio):
#   bash kubernetes/audits/importar_dashboard_audits.sh
# =============================================================================
set -uo pipefail

NS="proyecto-final"
REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
DASHBOARD="$REPO_ROOT/kubernetes/audits/grafana/audits-dashboard.json"
GRAFANA_USER="grafana_admin"
GRAFANA_PASS="web3"
# Puertos locales poco comunes para no chocar con otros procesos de la Mac.
GRAFANA_PORT=13000
API_PORT=18001
LOG_DIR="$(mktemp -d)"
PF_PIDS=()

cleanup() { for p in "${PF_PIDS[@]:-}"; do kill "$p" 2>/dev/null || true; done; }
trap cleanup EXIT

paso() { printf '\n\033[1;34m==> %s\033[0m\n' "$*"; }
falla() { printf '\n\033[1;31mERROR: %s\033[0m\n' "$*"; exit 1; }

# Abre un port-forward y espera a que responda. $1=nombre $2=recurso $3=local:remoto $4=url de prueba
abrir_tunel() {
  local nombre="$1" recurso="$2" puertos="$3" url="$4" log="$LOG_DIR/$1.log"
  kubectl -n "$NS" port-forward "$recurso" "$puertos" >"$log" 2>&1 &
  PF_PIDS+=($!)
  for _ in $(seq 1 40); do
    curl -s -o /dev/null "$url" && { echo "Túnel $nombre listo ($url)"; return 0; }
    sleep 1
  done
  echo "--- salida de kubectl port-forward ($nombre) ---"; cat "$log"
  echo "--- pods ---"; kubectl -n "$NS" get pods -o wide
  falla "No se pudo abrir el túnel a $nombre"
}

paso "Esperando a que los pods estén listos"
kubectl -n "$NS" wait --for=condition=Ready pod -l app=grafana --timeout=180s || falla "Grafana no quedó Ready"
kubectl -n "$NS" wait --for=condition=Ready pod -l app=prometheus --timeout=180s || falla "Prometheus no quedó Ready"
kubectl -n "$NS" wait --for=condition=Ready pod -l app=audits-api --timeout=180s || falla "audits-api no quedó Ready"
kubectl -n "$NS" get pods

paso "Abriendo port-forwards (temporales)"
abrir_tunel grafana    deploy/grafana    "$GRAFANA_PORT:3000" "http://localhost:$GRAFANA_PORT/api/health"
abrir_tunel audits-api deploy/audits-api "$API_PORT:8001"     "http://localhost:$API_PORT/health"

paso "Importando dashboard en Grafana"
RESP="$(printf '{"dashboard": %s, "overwrite": true}' "$(cat "$DASHBOARD")" \
  | curl -sS -u "$GRAFANA_USER:$GRAFANA_PASS" -H 'Content-Type: application/json' \
      -X POST "http://localhost:$GRAFANA_PORT/api/dashboards/db" --data-binary @-)"
echo "$RESP"
echo "$RESP" | grep -q '"status":"success"' || falla "Grafana no aceptó el dashboard (ver respuesta arriba)"

paso "Generando tráfico de prueba (~1 minuto)"
API="http://localhost:$API_PORT"
for ronda in $(seq 1 30); do
  id=$((900000 + RANDOM))
  curl -s -o /dev/null -X POST "$API/auditorias" -H 'Content-Type: application/json' \
    -d '{"id":'"$id"',"nombre":"Prueba metricas","usuario":"juan.cervantes","fecha":"2026-11-13T10:00:00"}'
  curl -s -o /dev/null "$API/auditorias"
  curl -s -o /dev/null "$API/auditorias/$id"
  curl -s -o /dev/null -X PUT "$API/auditorias/$id" -H 'Content-Type: application/json' -d '{"nombre":"Editada"}'
  curl -s -o /dev/null "$API/auditorias/999999999"                                                 # 404
  curl -s -o /dev/null -X POST "$API/auditorias" -H 'Content-Type: application/json' -d '{"id":"x"}' # 422
  curl -s -o /dev/null -X DELETE "$API/auditorias/$id"
  printf '.'
  sleep 2
done
echo

paso "Listo"
cat <<EOF
Para ver los resultados abre los túneles en otra terminal y déjalos corriendo:
  kubectl -n $NS port-forward deploy/prometheus 9090:9090
      -> http://localhost:9090/targets   (job "auditorias" en UP)
  kubectl -n $NS port-forward deploy/grafana $GRAFANA_PORT:3000
      -> http://localhost:$GRAFANA_PORT/d/audits-api   (usuario $GRAFANA_USER / $GRAFANA_PASS)
EOF
