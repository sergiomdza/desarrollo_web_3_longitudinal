#!/usr/bin/env bash
# Genera tráfico variado contra el servicio de reportes para poblar métricas y logs.
# Uso (con el port-forward corriendo en otra terminal):
#   bash generar_trafico.sh [vueltas]
set -u

BASE="${BASE_URL:-http://localhost:8000}"
VUELTAS="${1:-1}"
TMP="$(mktemp)"
trap 'rm -f "$TMP"' EXIT

PAYLOAD='{"titulo":"Uso de laptops - Noviembre","tipo":"uso_activos","descripcion":"Reporte de prueba","periodo_inicio":"2026-11-01T00:00:00Z","periodo_fin":"2026-11-30T23:59:59Z","generado_por":"equipo3","metricas":{"total_prestamos":10}}'

req() {
  local metodo="$1" ruta="$2" cuerpo="${3:-}"
  if [ -n "$cuerpo" ]; then
    curl -s -o "$TMP" -w "%{http_code}" -X "$metodo" "$BASE$ruta" -H "Content-Type: application/json" -d "$cuerpo"
  else
    curl -s -o "$TMP" -w "%{http_code}" -X "$metodo" "$BASE$ruta"
  fi
}

mostrar() { printf '%-7s %-34s -> %s\n' "$1" "$2" "$3"; }

for i in $(seq 1 "$VUELTAS"); do
  echo "== Vuelta $i =="

  code=$(req POST /reportes "$PAYLOAD"); mostrar POST /reportes "$code"
  ID=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["id"])' "$TMP" 2>/dev/null || true)
  if [ -z "$ID" ]; then
    echo "No se pudo crear el reporte. Respuesta:"; cat "$TMP"; echo
    continue
  fi

  code=$(req GET /reportes);                    mostrar GET  /reportes "$code"
  code=$(req GET "/reportes/$ID");              mostrar GET  "/reportes/{id}" "$code"
  code=$(req PUT "/reportes/$ID" '{"titulo":"Uso de laptops - Noviembre (revisado)"}'); mostrar PUT "/reportes/{id}" "$code"
  code=$(req DELETE "/reportes/$ID");           mostrar DELETE "/reportes/{id}" "$code"

  code=$(req GET "/reportes/$ID");              mostrar GET  "/reportes/{id} (ya borrado)" "$code"
  code=$(req GET /reportes/no-es-un-id);        mostrar GET  "/reportes/no-es-un-id" "$code"
  code=$(req POST /reportes '{"titulo":"x"}');  mostrar POST "/reportes (payload invalido)" "$code"
  code=$(req GET /ruta-inexistente);            mostrar GET  /ruta-inexistente "$code"

  code=$(req GET /health);                      mostrar GET  /health "$code"
  code=$(req GET /metrics);                     mostrar GET  /metrics "$code"
done
