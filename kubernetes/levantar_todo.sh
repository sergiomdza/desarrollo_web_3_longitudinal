#!/usr/bin/env bash
# =============================================================================
# Levanta los 6 microservicios + MongoDB + Prometheus + Grafana + Loki + Alloy
# en el cluster Kind "web3" (namespace proyecto-final) e importa los dashboards.
#
# Uso (desde cualquier carpeta):
#   bash kubernetes/levantar_todo.sh
#
#   Las imágenes NO se construyen en local: todos los Deployments jalan de GHCR
#   la imagen que publica GitHub Actions (imagePullPolicy: Always).
#
# Variables opcionales:
#   CLUSTER=web3    nombre del cluster Kind.
#   TIMEOUT=300s    espera máxima por cada rollout.
#
# Servicios (Service : puerto)           Deployment
#   products      categorias-ubicaciones-service : 8000   categorias-ubicaciones-api
#   users         users-service : 8000                    backend
#   requests      requests-service : 8000                 requests-backend
#   reports       reportes-service : 8000                 reportes-backend
#   audits        audits-service : 8001                   audits-api
#   notifications notificaciones : 80 (-> 8000)           notificaciones
# =============================================================================
set -euo pipefail

CLUSTER="${CLUSTER:-web3}"
NS="proyecto-final"
TIMEOUT="${TIMEOUT:-300s}"
GRAFANA_USER="grafana_admin"
GRAFANA_PASS="web3"
GRAFANA_LOCAL_PORT=13000

K8S="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FALLOS=()
PF_PID=""

paso() { printf '\n\033[1;36m==> %s\033[0m\n' "$*"; }
aviso() { printf '\033[1;33m!! %s\033[0m\n' "$*"; }
cleanup() { [ -n "$PF_PID" ] && kill "$PF_PID" 2>/dev/null || true; }
trap cleanup EXIT

# Espera un rollout; si falla lo registra y sigue con el resto.
esperar() {
  local tipo="$1" nombre="$2"
  kubectl -n "$NS" rollout status "$tipo/$nombre" --timeout="$TIMEOUT" \
    || FALLOS+=("$tipo/$nombre")
}

# Importa un dashboard en Grafana. $1=archivo json  $2=uid del datasource Prometheus
importar_dashboard() {
  local archivo="$1" prom_uid="$2" body resp code out
  body="$("$PY" - "$archivo" "$prom_uid" <<'PY'
import json, sys
raw = open(sys.argv[1], encoding="utf-8").read()
# El dashboard de requests trae un uid de datasource fijo de otro Grafana.
raw = raw.replace("PBFA97CFB590B2093", sys.argv[2])
print(json.dumps({"dashboard": json.loads(raw), "overwrite": True}))
PY
)"
  # La respuesta y el código HTTP van juntos (sin archivos temporales: /tmp no
  # existe para el Python nativo de Windows).
  resp="$(printf '%s' "$body" | curl -s -w '\n%{http_code}' \
    -u "$GRAFANA_USER:$GRAFANA_PASS" -H 'Content-Type: application/json' \
    -X POST "http://localhost:$GRAFANA_LOCAL_PORT/api/dashboards/db" --data-binary @-)"
  code="${resp##*$'\n'}"
  out="${resp%$'\n'*}"
  if [ "$code" = "200" ]; then
    echo "  OK  $(basename "$archivo") -> $(printf '%s' "$out" | "$PY" -c 'import json,sys;print(json.load(sys.stdin).get("url",""))' | tr -d '\r')"
  else
    aviso "Falló $(basename "$archivo") (HTTP $code): $out"
    FALLOS+=("dashboard/$(basename "$archivo")")
  fi
}

# --- 0. Verificaciones -------------------------------------------------------
paso "Verificando herramientas"
for cmd in docker kind kubectl curl; do
  command -v "$cmd" >/dev/null || { echo "Falta '$cmd' en el PATH"; exit 1; }
done
# En Windows el ejecutable suele llamarse "python" (o "py"); "python3" puede ser un stub de la Microsoft Store.
PY=""
for cmd in python3 python py; do
  if "$cmd" -c 'import sys' >/dev/null 2>&1; then PY="$cmd"; break; fi
done
[ -n "$PY" ] || { echo "Falta Python 3 en el PATH (python3, python o py)"; exit 1; }
docker info >/dev/null 2>&1 || { echo "Docker no está corriendo. Abre Docker Desktop y reintenta."; exit 1; }

# --- 1. Cluster y namespace --------------------------------------------------
paso "Cluster Kind '$CLUSTER'"
if ! kind get clusters 2>/dev/null | grep -qx "$CLUSTER"; then
  kind create cluster --name "$CLUSTER" --config "$K8S/products/kind-config.yaml"
else
  echo "Ya existe, se reutiliza."
fi
kubectl config use-context "kind-$CLUSTER" >/dev/null
kubectl apply -f "$K8S/products/namespace.yaml"

# --- 2. MongoDB (compartido) -------------------------------------------------
paso "MongoDB"
kubectl apply -f "$K8S/mongo_statefulset.yaml"
esperar statefulset mongo

# --- 4. Microservicios -------------------------------------------------------
# No se aplica requests/secret.yaml: redefine "mongo-secret" y pisaría el de
# mongo_statefulset.yaml (el deployment de requests usa las mismas claves de usuario/password).
paso "Aplicando manifiestos de los 6 microservicios"
kubectl apply \
  -f "$K8S/products/secret.yaml" \
  -f "$K8S/products/backend_configmap.yaml" \
  -f "$K8S/products/backend_deployment.yaml" \
  -f "$K8S/products/observabilidad/metrics_service.yaml"
kubectl apply -f "$K8S/users/backend_deployment.yaml"
kubectl apply \
  -f "$K8S/requests/backend_configmap.yaml" \
  -f "$K8S/requests/backend_deployment.yaml"
kubectl apply -f "$K8S/reports/backend_deployment.yaml"
kubectl apply \
  -f "$K8S/audits/backend_deployment.yaml" \
  -f "$K8S/audits/metrics_service.yaml"
kubectl apply \
  -f "$K8S/notifications/configmap.yaml" \
  -f "$K8S/notifications/secret.yaml" \
  -f "$K8S/notifications/service.yaml" \
  -f "$K8S/notifications/deployment.yaml"

# Los tags `*-latest` no cambian: al re-ejecutar el script, reiniciar fuerza a
# jalar la última imagen publicada por el CI/CD.
kubectl -n "$NS" rollout restart deployment \
  categorias-ubicaciones-api backend requests-backend reportes-backend audits-api notificaciones

# --- 5. Monitoreo ------------------------------------------------------------
paso "Prometheus + Grafana + Loki + Alloy"
kubectl apply -f "$K8S/monitoring_tools.yaml"
kubectl apply -f "$K8S/logging.yaml"
# Reinicio para que tomen los ConfigMaps (Prometheus/Alloy no recargan solos).
kubectl -n "$NS" rollout restart deployment prometheus grafana alloy

paso "Esperando a que todo esté listo"
for d in categorias-ubicaciones-api backend requests-backend reportes-backend audits-api notificaciones \
         prometheus grafana loki alloy; do
  esperar deployment "$d"
done

# --- 6. Dashboards de Grafana -------------------------------------------------
paso "Importando dashboards en Grafana"
kubectl -n "$NS" port-forward svc/grafana-service "$GRAFANA_LOCAL_PORT:3000" >/dev/null 2>&1 &
PF_PID=$!
ok=0
for _ in $(seq 1 40); do
  curl -sf "http://localhost:$GRAFANA_LOCAL_PORT/api/health" >/dev/null && { ok=1; break; }
  sleep 1
done
if [ "$ok" = "1" ]; then
  PROM_UID="$(curl -s -u "$GRAFANA_USER:$GRAFANA_PASS" \
    "http://localhost:$GRAFANA_LOCAL_PORT/api/datasources/name/Prometheus" \
    | "$PY" -c 'import json,sys;print(json.load(sys.stdin)["uid"])' | tr -d '\r')"
  importar_dashboard "$K8S/products/observabilidad/grafana_dashboard.json"      "$PROM_UID"
  importar_dashboard "$K8S/requests/grafana-dashboard.json"                     "$PROM_UID"
  importar_dashboard "$K8S/audits/grafana/audits-dashboard.json"                "$PROM_UID"
  importar_dashboard "$K8S/notifications/grafana/notificaciones-dashboard.json" "$PROM_UID"
  importar_dashboard "$K8S/k6/grafana/k6-dashboard.json"                        "$PROM_UID"
else
  aviso "Grafana no respondió por el port-forward; dashboards no importados."
  FALLOS+=("grafana-port-forward")
fi

# --- 7. Resumen --------------------------------------------------------------
paso "Estado final"
kubectl get pods -n "$NS" -o wide
if [ "${#FALLOS[@]}" -gt 0 ]; then
  aviso "Con problemas: ${FALLOS[*]}"
  aviso "Revisa con: kubectl -n $NS describe pod <pod>  /  kubectl -n $NS logs deploy/<deployment>"
fi

cat <<EOF

Accesos (cada uno en una terminal aparte):
  kubectl -n $NS port-forward svc/grafana-service 3000:3000
      -> http://localhost:3000   ($GRAFANA_USER / $GRAFANA_PASS)   Explore -> Loki: {app="<servicio>"}
  kubectl -n $NS port-forward svc/prometheus-service 9090:9090
      -> http://localhost:9090/targets   (6 jobs en UP)

  kubectl -n $NS port-forward svc/categorias-ubicaciones-service 8000:8000   # products
  kubectl -n $NS port-forward svc/users-service 8001:8000                    # users
  kubectl -n $NS port-forward svc/requests-service 8002:8000                 # requests
  kubectl -n $NS port-forward svc/reportes-service 8003:8000                 # reports
  kubectl -n $NS port-forward svc/audits-service 8004:8001                   # audits
  kubectl -n $NS port-forward svc/notificaciones 8005:80                     # notifications
EOF

[ "${#FALLOS[@]}" -eq 0 ]
