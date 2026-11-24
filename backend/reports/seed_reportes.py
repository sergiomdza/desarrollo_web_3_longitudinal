"""Crea la colección del módulo e inyecta 10 reportes de ejemplo.

Uso (con el cluster de Kind arriba):
    kubectl port-forward -n proyecto-final svc/mongo-service 27017:27017
    export MONGO_URI="mongodb://<user>:<pass>@localhost:27017/?authSource=admin"
    export MONGO_DB="desarrollo_web_3"
    export MONGO_COLLECTION="reportes_analitica"
    poetry run python seed_reportes.py [--reset]
"""
import os
import sys
from datetime import datetime, timezone

from pymongo import MongoClient


def d(y, m, day):
    return datetime(y, m, day, tzinfo=timezone.utc)


REPORTES = [
    ("Uso de laptops - Septiembre", "uso_activos", d(2026, 9, 1), d(2026, 9, 30), "ana.lopez", {"total_prestamos": 142, "horas_uso_promedio": 4.5, "tasa_ocupacion": 0.78}),
    ("Préstamos de proyectores - Agosto", "prestamos", d(2026, 8, 1), d(2026, 8, 31), "carlos.ruiz", {"total_prestamos": 57, "devoluciones_tardias": 6, "tasa_ocupacion": 0.41}),
    ("Inventario de laboratorio de redes", "inventario", d(2026, 9, 1), d(2026, 9, 30), "maria.diaz", {"activos_totales": 210, "activos_disponibles": 163, "activos_en_mantenimiento": 9}),
    ("Mantenimientos del semestre", "mantenimiento", d(2026, 8, 1), d(2026, 9, 30), "jorge.perez", {"mantenimientos_realizados": 34, "costo_total": 18250.0, "tiempo_promedio_dias": 3.2}),
    ("Uso de cámaras - Septiembre", "uso_activos", d(2026, 9, 1), d(2026, 9, 30), "ana.lopez", {"total_prestamos": 38, "horas_uso_promedio": 6.1, "tasa_ocupacion": 0.52}),
    ("Préstamos por departamento - Q3", "prestamos", d(2026, 7, 1), d(2026, 9, 30), "luis.herrera", {"total_prestamos": 420, "departamentos_activos": 8, "devoluciones_tardias": 21}),
    ("Inventario de biblioteca", "inventario", d(2026, 9, 15), d(2026, 9, 15), "sofia.castro", {"activos_totales": 96, "activos_disponibles": 80, "activos_en_mantenimiento": 2}),
    ("Activos más solicitados", "uso_activos", d(2026, 8, 1), d(2026, 9, 30), "carlos.ruiz", {"total_prestamos": 310, "activos_distintos": 45, "tasa_ocupacion": 0.69}),
    ("Equipos con mantenimiento recurrente", "mantenimiento", d(2026, 1, 1), d(2026, 9, 30), "maria.diaz", {"equipos_afectados": 12, "mantenimientos_realizados": 29, "costo_total": 12400.0}),
    ("Devoluciones tardías - Septiembre", "prestamos", d(2026, 9, 1), d(2026, 9, 30), "jorge.perez", {"total_prestamos": 142, "devoluciones_tardias": 11, "dias_retraso_promedio": 2.4}),
]


def main():
    client = MongoClient(os.environ["MONGO_URI"], serverSelectionTimeoutMS=5000)
    col = client[os.environ["MONGO_DB"]][os.environ["MONGO_COLLECTION"]]

    if "--reset" in sys.argv:
        col.delete_many({})
    elif col.count_documents({}) > 0:
        print("La colección ya tiene datos. Usa --reset para reiniciarla.")
        return

    ahora = datetime.now(timezone.utc)
    docs = [
        {
            "titulo": t,
            "tipo": tipo,
            "descripcion": f"Reporte automático: {t.lower()}.",
            "periodo_inicio": ini,
            "periodo_fin": fin,
            "generado_por": autor,
            "metricas": metricas,
            "creado_en": ahora,
        }
        for t, tipo, ini, fin, autor, metricas in REPORTES
    ]
    result = col.insert_many(docs)
    print(f"Insertados {len(result.inserted_ids)} reportes en '{col.name}'.")


if __name__ == "__main__":
    main()
