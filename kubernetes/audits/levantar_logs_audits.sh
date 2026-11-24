#!/usr/bin/env bash
# =============================================================================
# Levanta la recolección de logs (Loki + Alloy) en el cluster local de Kind.
#
# Uso (desde la raíz del repositorio):
#   bash kubernetes/audits/levantar_logs_audits.sh
#
# Qué hace:
#   1. Aplica kubernetes/logging.yaml en proyecto-final.
#   2. Reinicia Alloy para que tome la configuración nueva.
#   3. Verifica que Loki y Alloy estén disponibles.
#
# Después, en Grafana -> Explore -> datasource "Loki" se consultan con:
#   {app="audits-api"}
# =============================================================================

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"

kubectl apply -n proyecto-final -f "$REPO_ROOT/kubernetes/logging.yaml"

kubectl -n proyecto-final rollout restart deployment alloy

kubectl -n proyecto-final rollout status deployment loki --timeout=180s

kubectl -n proyecto-final rollout status deployment alloy --timeout=180s

echo "Listo. Consulta los logs en Grafana (Explore -> Loki) con: {app=\"audits-api\"}"