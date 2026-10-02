import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import asyncio
from datetime import datetime, timezone

from pymongo import AsyncMongoClient, UpdateOne

from app.db import COLLECTION_NAME, build_mongo_uri, require_env


SEED_DATA = [
    {
        "codigo": "SEED-001",
        "tipo": "recordatorio_devolucion",
        "canal": "email",
        "destinatario_id": "USR-001",
        "prestamo_id": "PREST-001",
        "titulo": "Recordatorio de devolución",
        "mensaje": "Tu préstamo debe ser devuelto próximamente.",
        "estado": "pendiente",
        "fecha_programada": datetime(2026, 10, 3, 15, 0, tzinfo=timezone.utc),
        "leida_at": None,
    },
    {
        "codigo": "SEED-002",
        "tipo": "alerta_vencimiento",
        "canal": "whatsapp",
        "destinatario_id": "USR-002",
        "prestamo_id": "PREST-002",
        "titulo": "Préstamo próximo a vencer",
        "mensaje": "Tu préstamo vence en 24 horas.",
        "estado": "enviada",
        "fecha_programada": datetime(2026, 10, 2, 12, 0, tzinfo=timezone.utc),
        "leida_at": None,
    },
    {
        "codigo": "SEED-003",
        "tipo": "confirmacion_aprobacion",
        "canal": "in_app",
        "destinatario_id": "USR-003",
        "prestamo_id": "PREST-003",
        "titulo": "Préstamo aprobado",
        "mensaje": "Tu solicitud de préstamo fue aprobada.",
        "estado": "leida",
        "fecha_programada": None,
        "leida_at": datetime(2026, 10, 1, 14, 30, tzinfo=timezone.utc),
    },
    {
        "codigo": "SEED-004",
        "tipo": "confirmacion_rechazo",
        "canal": "email",
        "destinatario_id": "USR-004",
        "prestamo_id": "PREST-004",
        "titulo": "Solicitud rechazada",
        "mensaje": "Tu solicitud de préstamo no fue aprobada.",
        "estado": "enviada",
        "fecha_programada": None,
        "leida_at": None,
    },
    {
        "codigo": "SEED-005",
        "tipo": "alerta_vencimiento",
        "canal": "push",
        "destinatario_id": "USR-005",
        "prestamo_id": "PREST-005",
        "titulo": "Alerta de vencimiento",
        "mensaje": "Tu préstamo vence mañana.",
        "estado": "pendiente",
        "fecha_programada": datetime(2026, 10, 2, 9, 0, tzinfo=timezone.utc),
        "leida_at": None,
    },
    {
        "codigo": "SEED-006",
        "tipo": "recordatorio_devolucion",
        "canal": "whatsapp",
        "destinatario_id": "USR-006",
        "prestamo_id": "PREST-006",
        "titulo": "Devolución pendiente",
        "mensaje": "Recuerda devolver el material prestado.",
        "estado": "enviada",
        "fecha_programada": datetime(2026, 10, 4, 11, 0, tzinfo=timezone.utc),
        "leida_at": None,
    },
    {
        "codigo": "SEED-007",
        "tipo": "confirmacion_aprobacion",
        "canal": "email",
        "destinatario_id": "USR-007",
        "prestamo_id": "PREST-007",
        "titulo": "Préstamo confirmado",
        "mensaje": "Tu préstamo fue aprobado correctamente.",
        "estado": "leida",
        "fecha_programada": None,
        "leida_at": datetime(2026, 9, 30, 18, 0, tzinfo=timezone.utc),
    },
    {
        "codigo": "SEED-008",
        "tipo": "notificacion_general",
        "canal": "in_app",
        "destinatario_id": "USR-008",
        "prestamo_id": "PREST-008",
        "titulo": "Actualización del sistema",
        "mensaje": "Tu información de préstamo fue actualizada.",
        "estado": "enviada",
        "fecha_programada": None,
        "leida_at": None,
    },
    {
        "codigo": "SEED-009",
        "tipo": "alerta_vencimiento",
        "canal": "push",
        "destinatario_id": "USR-009",
        "prestamo_id": "PREST-009",
        "titulo": "Último día de préstamo",
        "mensaje": "Hoy es el último día para devolver tu préstamo.",
        "estado": "pendiente",
        "fecha_programada": datetime(2026, 10, 1, 8, 0, tzinfo=timezone.utc),
        "leida_at": None,
    },
    {
        "codigo": "SEED-010",
        "tipo": "recordatorio_devolucion",
        "canal": "email",
        "destinatario_id": "USR-010",
        "prestamo_id": "PREST-010",
        "titulo": "Recordatorio final",
        "mensaje": "Este es un recordatorio final de devolución.",
        "estado": "fallida",
        "fecha_programada": datetime(2026, 10, 1, 16, 0, tzinfo=timezone.utc),
        "leida_at": None,
    },
]


async def seed():
    mongo_uri = build_mongo_uri()
    database_name = require_env("MONGO_DB")

    client = AsyncMongoClient(
        mongo_uri,
        serverSelectionTimeoutMS=5000,
    )

    try:
        await client.admin.command("ping")

        database = client[database_name]
        collection = database[COLLECTION_NAME]

        await collection.create_index(
            "codigo",
            unique=True,
        )

        now = datetime.now(timezone.utc)

        operations = []

        for item in SEED_DATA:
            document = {
                **item,
                "created_at": now,
                "updated_at": now,
            }

            operations.append(
                UpdateOne(
                    {"codigo": item["codigo"]},
                    {"$set": document},
                    upsert=True,
                )
            )

        result = await collection.bulk_write(
            operations
        )

        total = await collection.count_documents({})

        print("====================================")
        print("SEEDER DE NOTIFICACIONES")
        print("====================================")
        print(f"Registros procesados: {len(SEED_DATA)}")
        print(f"Nuevos: {len(result.upserted_ids)}")
        print(f"Total en colección: {total}")
        print("====================================")

    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(seed())