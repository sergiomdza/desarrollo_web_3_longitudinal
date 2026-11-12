#!/usr/bin/env python3
"""Siembra la colección de activos del Equipo 2 (Categorías & Ubicaciones).

Se conecta al MongoDB que corre en el cluster de Kubernetes, crea las
colecciones del módulo e inserta 10 activos congruentes con el dominio.

Ninguna credencial está escrita en el código: la configuración sale del
Secret y del ConfigMap del cluster (modo por defecto) o de variables de
entorno (`--env`).

Uso:
    # 1) Modo cluster (default): lee Secret/ConfigMap de proyecto-final y abre
    #    el port-forward a mongo-service por su cuenta.
    python scripts/seed_activos.py

    # 2) Modo variables de entorno (docker compose, o Job dentro del cluster)
    python scripts/seed_activos.py --env

    # Borra lo que haya antes de insertar
    python scripts/seed_activos.py --drop
"""

import argparse
import base64
import json
import os
import socket
import subprocess
import sys
import time
from contextlib import closing, contextmanager
from typing import Any, Iterator
from urllib.parse import urlsplit, urlunsplit

from pymongo import MongoClient
from pymongo.errors import CollectionInvalid, PyMongoError

NAMESPACE = "proyecto-final"
SECRET_NAME = "categorias-ubicaciones-secret"
CONFIGMAP_NAME = "categorias-ubicaciones-config"
MONGO_SERVICE = "mongo-service"
MONGO_PORT = 27017


# --------------------------------------------------------------------------
# Datos a insertar: 10 activos del catálogo institucional
# --------------------------------------------------------------------------
ACTIVOS: list[dict[str, Any]] = [
    {
        "codigo": "TEC-001",
        "nombre": "Laptop Lenovo ThinkPad T14",
        "categoria": {"nombre": "Tecnología", "descripcion": "Equipo de cómputo y periféricos"},
        "ubicacion": {"nombre": "Laboratorio de Cómputo A", "sede": "Campus Norte", "piso": 2},
        "estado": "en_uso",
        "valor_adquisicion": 24500.0,
        "descripcion": "Asignada al laboratorio de desarrollo de software",
    },
    {
        "codigo": "TEC-002",
        "nombre": "Proyector Epson PowerLite X49",
        "categoria": {"nombre": "Tecnología", "descripcion": "Equipo de cómputo y periféricos"},
        "ubicacion": {"nombre": "Aula 204", "sede": "Campus Norte", "piso": 2},
        "estado": "disponible",
        "valor_adquisicion": 12800.5,
        "descripcion": "Proyector fijo con soporte de techo",
    },
    {
        "codigo": "TEC-003",
        "nombre": "Switch Cisco Catalyst 1000 24p",
        "categoria": {"nombre": "Infraestructura de red", "descripcion": "Equipo de networking"},
        "ubicacion": {"nombre": "Site de Telecomunicaciones", "sede": "Campus Norte", "piso": 0},
        "estado": "en_uso",
        "valor_adquisicion": 31990.0,
        "descripcion": "Distribución de red del edificio de ingeniería",
    },
    {
        "codigo": "MOB-001",
        "nombre": "Escritorio ejecutivo en L",
        "categoria": {"nombre": "Mobiliario", "descripcion": "Muebles de oficina y aulas"},
        "ubicacion": {"nombre": "Coordinación Académica", "sede": "Campus Centro", "piso": 1},
        "estado": "en_uso",
        "valor_adquisicion": 8450.0,
        "descripcion": "Escritorio de melamina con cajonera integrada",
    },
    {
        "codigo": "MOB-002",
        "nombre": "Lote de 30 sillas de paleta",
        "categoria": {"nombre": "Mobiliario", "descripcion": "Muebles de oficina y aulas"},
        "ubicacion": {"nombre": "Almacén General", "sede": "Campus Centro", "piso": 0},
        "estado": "disponible",
        "valor_adquisicion": 21000.0,
        "descripcion": "Sillas nuevas en resguardo para el siguiente ciclo",
    },
    {
        "codigo": "LAB-001",
        "nombre": "Microscopio binocular Olympus CX23",
        "categoria": {"nombre": "Equipo de laboratorio", "descripcion": "Instrumentos de práctica y medición"},
        "ubicacion": {"nombre": "Laboratorio de Biología", "sede": "Campus Sur", "piso": 3},
        "estado": "mantenimiento",
        "valor_adquisicion": 46300.0,
        "descripcion": "En calibración anual con el proveedor",
    },
    {
        "codigo": "LAB-002",
        "nombre": "Osciloscopio Tektronix TBS1052C",
        "categoria": {"nombre": "Equipo de laboratorio", "descripcion": "Instrumentos de práctica y medición"},
        "ubicacion": {"nombre": "Laboratorio de Electrónica", "sede": "Campus Sur", "piso": 1},
        "estado": "disponible",
        "valor_adquisicion": 18750.0,
        "descripcion": "Uso en prácticas de circuitos analógicos",
    },
    {
        "codigo": "AUD-001",
        "nombre": "Consola de audio Yamaha MG12XU",
        "categoria": {"nombre": "Audio y video", "descripcion": "Equipo de producción audiovisual"},
        "ubicacion": {"nombre": "Auditorio Principal", "sede": "Campus Centro", "piso": 1},
        "estado": "en_uso",
        "valor_adquisicion": 15600.0,
        "descripcion": "Mezcladora del sistema de sonido del auditorio",
    },
    {
        "codigo": "VEH-001",
        "nombre": "Camioneta Nissan Urvan 2019",
        "categoria": {"nombre": "Vehículos", "descripcion": "Parque vehicular institucional"},
        "ubicacion": {"nombre": "Estacionamiento de Servicios", "sede": "Campus Norte", "piso": 0},
        "estado": "disponible",
        "valor_adquisicion": 389000.0,
        "descripcion": "Transporte de alumnos a prácticas de campo",
    },
    {
        "codigo": "TEC-004",
        "nombre": "Impresora HP LaserJet Pro M404",
        "categoria": {"nombre": "Tecnología", "descripcion": "Equipo de cómputo y periféricos"},
        "ubicacion": {"nombre": "Almacén General", "sede": "Campus Centro", "piso": 0},
        "estado": "baja",
        "valor_adquisicion": 7300.0,
        "descripcion": "Fuera de servicio, en espera de dictamen para desecho",
    },
]


# --------------------------------------------------------------------------
# Configuración
# --------------------------------------------------------------------------
def _required_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        sys.exit(f"ERROR: falta la variable de entorno requerida: {name}")
    return value


def _kubectl(*args: str) -> str:
    """Corre kubectl y regresa su stdout; aborta con un mensaje claro si falla."""
    try:
        result = subprocess.run(
            ("kubectl",) + args,
            capture_output=True,
            text=True,
            check=True,
        )
    except FileNotFoundError:
        sys.exit("ERROR: no se encontró 'kubectl'. Instálalo o usa --env.")
    except subprocess.CalledProcessError as exc:
        sys.exit(
            f"ERROR: falló 'kubectl {' '.join(args)}'.\n"
            f"{exc.stderr.strip()}\n\n"
            "¿Ya corriste kubernetes/equipo_2/setup_app.sh?"
        )
    return result.stdout


def _config_from_env() -> dict[str, str]:
    """Configuración desde variables de entorno (igual que database.py)."""
    return {
        "mongo_uri": _required_env("MONGO_URI"),
        "db_name": _required_env("MONGO_DB_NAME"),
        "activos": _required_env("ACTIVOS_COLLECTION"),
        "categorias": _required_env("CATEGORIAS_COLLECTION"),
        "ubicaciones": _required_env("UBICACIONES_COLLECTION"),
    }


def _config_from_cluster() -> dict[str, str]:
    """Configuración leída del Secret y el ConfigMap del namespace proyecto-final."""
    secret = json.loads(_kubectl("get", "secret", SECRET_NAME, "-n", NAMESPACE, "-o", "json"))
    config = json.loads(_kubectl("get", "configmap", CONFIGMAP_NAME, "-n", NAMESPACE, "-o", "json"))

    mongo_uri = base64.b64decode(secret["data"]["MONGO_URI"]).decode()
    data = config.get("data", {})

    return {
        "mongo_uri": mongo_uri,
        "db_name": data["MONGO_DB_NAME"],
        "activos": data["ACTIVOS_COLLECTION"],
        "categorias": data["CATEGORIAS_COLLECTION"],
        "ubicaciones": data["UBICACIONES_COLLECTION"],
    }


def _rewrite_host(mongo_uri: str, host: str, port: int) -> str:
    """Apunta el URI del cluster al extremo local del port-forward.

    Conserva usuario, contraseña y query string (authSource) del URI original.
    """
    parts = urlsplit(mongo_uri)
    credentials = ""
    if parts.username:
        credentials = parts.username
        if parts.password:
            credentials += f":{parts.password}"
        credentials += "@"
    return urlunsplit((parts.scheme, f"{credentials}{host}:{port}", parts.path, parts.query, parts.fragment))


def _free_port() -> int:
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@contextmanager
def _port_forward(local_port: int) -> Iterator[None]:
    """Abre `kubectl port-forward` a mongo-service y lo cierra al salir."""
    print(f"==> Abriendo port-forward a {MONGO_SERVICE} en 127.0.0.1:{local_port}...")
    process = subprocess.Popen(
        [
            "kubectl", "port-forward", "-n", NAMESPACE,
            f"service/{MONGO_SERVICE}", f"{local_port}:{MONGO_PORT}",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            if process.poll() is not None:
                sys.exit(
                    "ERROR: el port-forward terminó antes de establecerse.\n"
                    f"{(process.stderr.read() if process.stderr else '').strip()}"
                )
            with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
                sock.settimeout(1)
                if sock.connect_ex(("127.0.0.1", local_port)) == 0:
                    break
            time.sleep(0.5)
        else:
            sys.exit("ERROR: el port-forward no respondió después de 30s.")
        yield
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
        print("==> Port-forward cerrado.")


# --------------------------------------------------------------------------
# Siembra
# --------------------------------------------------------------------------
def _ensure_collection(db, name: str) -> None:
    """Crea la colección si no existe (Mongo también la crea al insertar)."""
    try:
        db.create_collection(name)
        print(f"    + colección '{name}' creada")
    except CollectionInvalid:
        print(f"    = colección '{name}' ya existía")


def seed(mongo_uri: str, config: dict[str, str], drop: bool) -> None:
    client = MongoClient(mongo_uri, serverSelectionTimeoutMS=10000)
    try:
        client.admin.command("ping")
    except PyMongoError as exc:
        sys.exit(f"ERROR: no se pudo conectar a MongoDB.\n{exc}")

    db = client[config["db_name"]]
    print(f"==> Conectado a MongoDB, base de datos '{config['db_name']}'")

    collections = (config["activos"], config["categorias"], config["ubicaciones"])

    if drop:
        for name in collections:
            db[name].drop()
            print(f"    - colección '{name}' eliminada (--drop)")

    for name in collections:
        _ensure_collection(db, name)

    activos = db[config["activos"]]

    # Upsert por 'codigo': el script se puede correr varias veces sin duplicar.
    for activo in ACTIVOS:
        activos.replace_one({"codigo": activo["codigo"]}, activo, upsert=True)

    # Índices que respaldan los filtros de GET /activos
    activos.create_index("codigo")
    activos.create_index("estado")
    activos.create_index("categoria.nombre")
    activos.create_index("ubicacion.nombre")

    # Catálogos derivados de los activos (las otras dos colecciones del módulo)
    for key, field in (("categorias", "categoria"), ("ubicaciones", "ubicacion")):
        collection = db[config[key]]
        for item in {json.dumps(a[field], sort_keys=True) for a in ACTIVOS}:
            document = json.loads(item)
            collection.replace_one({"nombre": document["nombre"]}, document, upsert=True)
        print(f"    ✓ '{config[key]}': {collection.count_documents({})} documentos")

    print(f"    ✓ '{config['activos']}': {activos.count_documents({})} documentos")
    print("\n==> Listo. Muestra de los activos sembrados:")
    for document in activos.find({}, {"_id": 0, "codigo": 1, "nombre": 1, "estado": 1}).limit(10):
        print(f"    {document['codigo']:<9} {document['nombre'][:42]:<44} {document['estado']}")

    client.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Crea las colecciones del módulo Categorías & Ubicaciones e inserta 10 activos.",
    )
    parser.add_argument(
        "--env",
        action="store_true",
        help="Toma la configuración de variables de entorno en lugar del cluster "
             "(útil con docker compose o corriendo dentro del cluster).",
    )
    parser.add_argument(
        "--drop",
        action="store_true",
        help="Borra las colecciones del módulo antes de insertar.",
    )
    parser.add_argument(
        "--local-port",
        type=int,
        default=None,
        help="Puerto local del port-forward (por defecto, uno libre al azar).",
    )
    args = parser.parse_args()

    if args.env:
        config = _config_from_env()
        print("==> Configuración tomada de variables de entorno")
        seed(config["mongo_uri"], config, args.drop)
        return

    print(f"==> Leyendo configuración del cluster (namespace '{NAMESPACE}')...")
    config = _config_from_cluster()
    local_port = args.local_port or _free_port()
    with _port_forward(local_port):
        seed(_rewrite_host(config["mongo_uri"], "127.0.0.1", local_port), config, args.drop)


if __name__ == "__main__":
    main()
