#!/usr/bin/env bash
#
# Crea la colección "auditorias" en MongoDB con validación de esquema.
# Campos: id, nombre, usuario, fecha.
#
# Sin pymongo: usa mongosh.
#   - Modo por defecto: ejecuta mongosh DENTRO del pod con kubectl exec
#     (no necesitas port-forward ni instalar nada; solo kubectl).
#   - Modo --local: usa un mongosh instalado en tu máquina contra localhost
#     (requiere abrir antes el túnel:
#      kubectl port-forward -n proyecto-final svc/mongo-service 27017:27017).
#
# Uso:
#   ./crear_auditorias.sh            # vía kubectl exec
#   ./crear_auditorias.sh --local    # vía mongosh local + port-forward

set -euo pipefail

# ---------------------------------------------------------------------------
# Variables de conexión (se pueden sobreescribir desde el entorno)
# ---------------------------------------------------------------------------
NAMESPACE="${NAMESPACE:-proyecto-final}"
POD="${POD:-}"                        # si está vacío, se detecta el primer pod "mongo"
MONGO_HOST="${MONGO_HOST:-localhost}"
MONGO_PORT="${MONGO_PORT:-27017}"
MONGO_USER="${MONGO_USER:-admin}"
MONGO_PASSWORD="${MONGO_PASSWORD:-web3}"
MONGO_AUTH_SOURCE="${MONGO_AUTH_SOURCE:-admin}"
MONGO_DB="${MONGO_DB:-DB_Proyecto}"
MONGO_COLLECTION="${MONGO_COLLECTION:-auditorias}"
MONGO_TIMEOUT_MS="${MONGO_TIMEOUT_MS:-5000}"

MODE="pod"
if [[ "${1:-}" == "--local" ]]; then
  MODE="local"
fi

# ---------------------------------------------------------------------------
# Lógica en JavaScript (se envía a mongosh por stdin)
# ---------------------------------------------------------------------------
js_script() {
cat <<EOF
const NOMBRE_DB = "${MONGO_DB}";
const NOMBRE_COL = "${MONGO_COLLECTION}";

const VALIDATOR = {
  \$jsonSchema: {
    bsonType: "object",
    required: ["id", "nombre", "usuario", "fecha"],
    properties: {
      id:      { bsonType: "int",    description: "Identificador de la auditoría (entero, único)" },
      nombre:  { bsonType: "string", description: "Nombre o descripción de la acción auditada" },
      usuario: { bsonType: "string", description: "Usuario que realizó la acción" },
      fecha:   { bsonType: "date",   description: "Fecha y hora del evento" }
    }
  }
};

db.adminCommand({ ping: 1 });
print("Conectado a MongoDB");

const bd = db.getSiblingDB(NOMBRE_DB);

if (bd.getCollectionNames().includes(NOMBRE_COL)) {
  // Ya existe: actualiza el validador para mantenerlo al día
  bd.runCommand({ collMod: NOMBRE_COL, validator: VALIDATOR });
  print("La colección '" + NOMBRE_COL + "' ya existía; validador actualizado.");
} else {
  bd.createCollection(NOMBRE_COL, { validator: VALIDATOR });
  print("Colección '" + NOMBRE_COL + "' creada.");
}

const col = bd.getCollection(NOMBRE_COL);
col.createIndex({ id: 1 },       { unique: true, name: "idx_id_unico" });
col.createIndex({ usuario: 1 },  { name: "idx_usuario" });
col.createIndex({ fecha: -1 },   { name: "idx_fecha" });
print("Índices creados: id (único), usuario, fecha.");

// Datos de ejemplo. Se usa upsert por "id", así puedes ejecutar el script
// varias veces sin errores de duplicados. NumberInt porque el esquema exige int.
const auditorias = [
  { id: NumberInt(1),  nombre: "Inicio de sesión",                    usuario: "admin",    fecha: ISODate("2026-09-28T08:02:00Z") },
  { id: NumberInt(2),  nombre: "Creación de usuario jgarcia",         usuario: "admin",    fecha: ISODate("2026-09-28T08:15:00Z") },
  { id: NumberInt(3),  nombre: "Creación de usuario mlopez",          usuario: "admin",    fecha: ISODate("2026-09-28T08:21:00Z") },
  { id: NumberInt(4),  nombre: "Inicio de sesión",                    usuario: "jgarcia",  fecha: ISODate("2026-09-28T09:05:00Z") },
  { id: NumberInt(5),  nombre: "Consulta de reporte de ventas",       usuario: "jgarcia",  fecha: ISODate("2026-09-28T09:32:00Z") },
  { id: NumberInt(6),  nombre: "Modificación de permisos de mlopez",  usuario: "admin",    fecha: ISODate("2026-09-28T10:10:00Z") },
  { id: NumberInt(7),  nombre: "Inicio de sesión",                    usuario: "mlopez",   fecha: ISODate("2026-09-28T10:45:00Z") },
  { id: NumberInt(8),  nombre: "Exportación de reporte de inventario", usuario: "mlopez",  fecha: ISODate("2026-09-28T11:20:00Z") },
  { id: NumberInt(9),  nombre: "Cambio de contraseña",                usuario: "jgarcia",  fecha: ISODate("2026-09-28T12:03:00Z") },
  { id: NumberInt(10), nombre: "Cierre de sesión",                    usuario: "mlopez",   fecha: ISODate("2026-09-28T13:30:00Z") }
];

const res = col.bulkWrite(
  auditorias.map(function (a) {
    return { replaceOne: { filter: { id: a.id }, replacement: a, upsert: true } };
  })
);
print("Auditorías de ejemplo: " + res.upsertedCount + " insertadas, " + res.modifiedCount + " actualizadas.");
print("Total de documentos en '" + NOMBRE_COL + "': " + col.countDocuments({}));

print("Colecciones en '" + NOMBRE_DB + "': " + JSON.stringify(bd.getCollectionNames()));
EOF
}

# ---------------------------------------------------------------------------
# Ejecución
# ---------------------------------------------------------------------------
MONGOSH_ARGS=(
  --quiet --norc
  --username "$MONGO_USER"
  --password "$MONGO_PASSWORD"
  --authenticationDatabase "$MONGO_AUTH_SOURCE"
)

if [[ "$MODE" == "local" ]]; then
  command -v mongosh >/dev/null 2>&1 || {
    echo "ERROR: mongosh no está instalado. Usa el modo por defecto (kubectl exec)." >&2
    exit 1
  }
  echo "Modo local: conectando a ${MONGO_HOST}:${MONGO_PORT}"
  js_script | mongosh "mongodb://${MONGO_HOST}:${MONGO_PORT}/?serverSelectionTimeoutMS=${MONGO_TIMEOUT_MS}" \
    "${MONGOSH_ARGS[@]}" \
    || { echo "ERROR de MongoDB: revisa el port-forward y las credenciales." >&2; exit 1; }
else
  command -v kubectl >/dev/null 2>&1 || {
    echo "ERROR: kubectl no está instalado." >&2
    exit 1
  }
  if [[ -z "$POD" ]]; then
    POD="$(kubectl get pods -n "$NAMESPACE" -o name | grep -m1 -i mongo | sed 's|^pod/||' || true)"
  fi
  [[ -n "$POD" ]] || {
    echo "ERROR: no se encontró un pod de mongo en el namespace '$NAMESPACE' (define POD=...)." >&2
    exit 1
  }
  echo "Modo pod: ejecutando mongosh en ${NAMESPACE}/${POD}"
  js_script | kubectl exec -i -n "$NAMESPACE" "$POD" -- mongosh "${MONGOSH_ARGS[@]}" \
    || { echo "ERROR de MongoDB: revisa el pod y las credenciales." >&2; exit 1; }
fi