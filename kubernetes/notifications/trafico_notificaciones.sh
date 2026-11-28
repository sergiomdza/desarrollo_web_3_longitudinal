#!/usr/bin/env bash
# =============================================================================
# Equipo 6 - Genera tráfico contra el servicio de notificaciones para la demo:
# CRUD completo + un 404 + un 422 (+ /health y /metrics).
#
# Requiere el port-forward abierto:
#   kubectl -n proyecto-final port-forward svc/notificaciones 8001:80
#
# Uso:
#   bash kubernetes/notifications/trafico_notificaciones.sh [rondas]
#   API=http://localhost:8005 bash kubernetes/notifications/trafico_notificaciones.sh 10
# =============================================================================
set -u

RONDAS="${1:-1}"
API="${API:-http://localhost:8001}"
TMP="$(mktemp)"
trap 'rm -f "$TMP"' EXIT

# Llama al endpoint, guarda la respuesta en $TMP e imprime método, ruta y código HTTP.
llamar() {
  local metodo="$1" ruta="$2" cuerpo="${3:-}" code
  if [ -n "$cuerpo" ]; then
    code=$(curl -s -o "$TMP" -w '%{http_code}' -X "$metodo" "$API$ruta" \
      -H 'Content-Type: application/json' --data-binary "$cuerpo")
  else
    code=$(curl -s -o "$TMP" -w '%{http_code}' -X "$metodo" "$API$ruta")
  fi
  printf '%-6s %-45s -> %s\n' "$metodo" "$ruta" "$code"
}

for r in $(seq 1 "$RONDAS"); do
  codigo="DEMO-$((RANDOM * 32768 + RANDOM))"
  nueva='{"codigo":"'"$codigo"'","tipo":"notificacion_general","canal":"email","destinatario_id":"usuario-demo","titulo":"Prueba demo","mensaje":"Hola desde la demo"}'

  llamar POST /notificaciones "$nueva"
  id="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["id"])' "$TMP" 2>/dev/null || true)"
  if [ -z "$id" ]; then
    echo "No se pudo crear la notificación. Respuesta:"; cat "$TMP"; echo
    continue
  fi

  llamar GET    "/notificaciones"
  llamar GET    "/notificaciones/$id"
  llamar PUT    "/notificaciones/$id" '{"titulo":"Prueba demo (editada)","estado":"enviada"}'
  llamar DELETE "/notificaciones/$id"
  llamar GET    "/notificaciones/000000000000000000000000"           # 404: ID inexistente
  llamar POST   "/notificaciones" '{"codigo":"x","tipo":"no_existe"}' # 422: payload inválido
  [ "$RONDAS" -gt 1 ] && sleep 0.5
done

llamar GET /health
llamar GET /metrics
