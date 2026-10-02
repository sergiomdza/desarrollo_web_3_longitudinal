import pymongo
#Cambiar por los del .env
client = pymongo.MongoClient("mongodb://admin:web3@localhost:27017/?authSource=admin")

theDatabase = client ["database_proyecto"]

column = theDatabase["Requests"]

tableInserts = [
    {
    "id_activo" : 1,
	"name": "cuenta de clientes",
	"approved_state": True,
	"receive_date": "2026-09-30T10:46:00.000Z",
	"return_date": "2026-10-01T10:46:00.000Z",
	"confirmation_state": "pending",
	"id_responsable": 1
    },
    {
    "id_activo" : 2,
	"name": "inventario de mercancias",
	"approved_state": False,
	"receive_date": "2026-09-30T10:46:00.000Z",
	"return_date": "2026-10-01T10:46:00.000Z",
	"confirmation_state": "vencido",
	"id_responsable": 2
    },
    {
    "id_activo" : 3,
	"name": "laptop numero 3",
	"approved_state": True,
	"receive_date": "2026-09-30T10:46:00.000Z",
	"return_date": "2026-10-01T10:46:00.000Z",
	"confirmation_state": "devuelto",
	"id_responsable": 10
    },
    {
    "id_activo" : 4,
	"name": "mouse",
	"approved_state": True,
	"receive_date": "2026-09-30T10:46:00.000Z",
	"return_date": "2026-10-01T10:46:00.000Z",
	"confirmation_state": "devuelto",
	"id_responsable": 10
    },
    {
    "id_activo" : 5,
	"name": "cuenta de luz",
	"approved_state": True,
	"receive_date": "2026-09-30T10:46:00.000Z",
	"return_date": "2026-10-01T10:46:00.000Z",
	"confirmation_state": "activo",
	"id_responsable": 5
    },
    {
    "id_activo" : 6,
	"name": "registros",
	"approved_state": True,
	"receive_date": "2026-09-30T10:46:00.000Z",
	"return_date": "2026-10-01T10:46:00.000Z",
	"confirmation_state": "pendiente",
	"id_responsable": 4
    },
    {
    "id_activo" : 7,
	"name": "20 hojas",
	"approved_state": True,
	"receive_date": "2026-09-30T10:46:00.000Z",
	"return_date": "2026-10-01T10:46:00.000Z",
	"confirmation_state": "devuelto",
	"id_responsable": 8
    },
    {
    "id_activo" : 8,
	"name": "registro del edificio",
	"approved_state": False,
	"receive_date": "2026-09-30T10:46:00.000Z",
	"return_date": "2026-10-01T10:46:00.000Z",
	"confirmation_state": "vencido",
	"id_responsable": 6
    },
    {
    "id_activo" : 9,
	"name": "cafetera",
	"approved_state": True,
	"receive_date": "2026-09-30T10:46:00.000Z",
	"return_date": "2026-10-01T10:46:00.000Z",
	"confirmation_state": "devuelto",
	"id_responsable": 7
    },
    {
    "id_activo" : 10,
	"name": "bolsas",
	"approved_state": False,
	"receive_date": "2026-09-30T10:46:00.000Z",
	"return_date": "2026-10-01T10:46:00.000Z",
	"confirmation_state": "vencido",
	"id_responsable": 9
    }
]

x = column.insert_many(tableInserts)
print(x.inserted_ids)

print(theDatabase.list_collection_names())
