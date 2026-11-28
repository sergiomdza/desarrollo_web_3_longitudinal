#!/usr/bin/env bash
# =============================================================================
# Corre una prueba de K6 como Job dentro del cluster Kind y muestra su resultado.
#
# Uso:
#   bash kubernetes/k6/correr_k6.sh smoke   # 1 VU, 30 s: ¿el servicio responde bien?
#   bash kubernetes/k6/correr_k6.sh load    # stages hasta 30 VUs, ~3.5 min
#
# Qué hace:
#   1. Publica scripts/*.js en el ConfigMap "k6-scripts".
#   2. Borra el Job anterior (un Job no se puede volver a ejecutar) y crea el nuevo.
#   3. Sigue los logs hasta que termine e indica si pasó o falló (thresholds).
#
# Requiere el stack levantado (kubernetes/levantar_todo.sh) y Prometheus con
# --web.enable-remote-write-receiver (ya está en monitoring_tools.yaml).
# =============================================================================
set -euo pipefail

NS="proyecto-final"
TEST="${1:-}"
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

case "$TEST" in
  smoke | load) ;;
  *) echo "Uso: bash $0 smoke|load"; exit 1 ;;
esac

JOB="k6-$TEST"

echo "==> Verificando que el servicio a probar esté arriba..."
kubectl -n "$NS" get deployment notificaciones >/dev/null \
  || { echo "No existe deployment/notificaciones en $NS. Corre primero kubernetes/levantar_todo.sh"; exit 1; }
kubectl -n "$NS" rollout status deployment/notificaciones --timeout=60s

echo "==> Publicando scripts en el ConfigMap k6-scripts..."
kubectl -n "$NS" create configmap k6-scripts --from-file="$DIR/scripts" \
  --dry-run=client -o yaml | kubectl apply -f -

echo "==> Creando el Job $JOB..."
kubectl -n "$NS" delete job "$JOB" --ignore-not-found --wait=true
kubectl apply -f "$DIR/job_$TEST.yaml"

echo "==> Esperando a que arranque el pod..."
kubectl -n "$NS" wait --for=condition=Ready pod -l "job-name=$JOB" --timeout=120s \
  || echo "(el pod pudo terminar antes de reportar Ready; se muestran los logs igual)"

echo "==> Logs de K6 (Ctrl+C solo deja de mostrarlos; la prueba sigue corriendo):"
kubectl -n "$NS" logs -f "job/$JOB" || true

echo "==> Resultado del Job:"
for _ in $(seq 1 30); do
  ok="$(kubectl -n "$NS" get job "$JOB" -o jsonpath='{.status.succeeded}')"
  ko="$(kubectl -n "$NS" get job "$JOB" -o jsonpath='{.status.failed}')"
  [ -n "$ok" ] || [ -n "$ko" ] && break
  sleep 1
done

if [ -n "${ok:-}" ]; then
  echo "✅ $JOB PASÓ: se cumplieron todos los thresholds."
else
  echo "❌ $JOB FALLÓ: algún threshold no se cumplió (revisa las líneas con ✗ arriba)."
  exit 1
fi

cat <<EOF

Para ver las métricas en Grafana:
  kubectl -n $NS port-forward svc/grafana-service 3000:3000
  -> http://localhost:3000/d/k6-notificaciones   (testid = $TEST)
EOF
