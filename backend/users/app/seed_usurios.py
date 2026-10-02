# scrip para mandar usuarios
import httpx

URL = ""

usuarios = [
    {
        "nombre": "Kevin",
        "apellido": "Vicente",
        "email": "kevin.vicente@email.com",
        "password": "Password123",
        "rol": "admin"
    },
    {
        "nombre": "Ana",
        "apellido": "Perez",
        "email": "ana.perez@email.com",
        "password": "Password123",
        "rol": "usuario"
    },
    {
        "nombre": "Carlos",
        "apellido": "Lopez",
        "email": "carlos.lopez@email.com",
        "password": "Password123",
        "rol": "moderador"
    },
    {
        "nombre": "Mariana",
        "apellido": "Garcia",
        "email": "mariana.garcia@email.com",
        "password": "Password123",
        "rol": "usuario"
    },
    {
        "nombre": "Luis",
        "apellido": "Hernandez",
        "email": "luis.hernandez@email.com",
        "password": "Password123",
        "rol": "usuario"
    },
    {
        "nombre": "Sofia",
        "apellido": "Martinez",
        "email": "sofia.martinez@email.com",
        "password": "Password123",
        "rol": "usuario"
    },
    {
        "nombre": "Diego",
        "apellido": "Ramirez",
        "email": "diego.ramirez@email.com",
        "password": "Password123",
        "rol": "moderador"
    },
    {
        "nombre": "Valeria",
        "apellido": "Torres",
        "email": "valeria.torres@email.com",
        "password": "Password123",
        "rol": "usuario"
    },
    {
        "nombre": "Fernando",
        "apellido": "Castro",
        "email": "fernando.castro@email.com",
        "password": "Password123",
        "rol": "usuario"
    },
    {
        "nombre": "Daniela",
        "apellido": "Morales",
        "email": "daniela.morales@email.com",
        "password": "Password123",
        "rol": "usuario"
    },
    {
        "nombre": "Jorge",
        "apellido": "Sanchez",
        "email": "jorge.sanchez@email.com",
        "password": "Password123",
        "rol": "moderador"
    },
    {
        "nombre": "Camila",
        "apellido": "Ruiz",
        "email": "camila.ruiz@email.com",
        "password": "Password123",
        "rol": "usuario"
    },
    {
        "nombre": "Miguel",
        "apellido": "Mendoza",
        "email": "miguel.mendoza@email.com",
        "password": "Password123",
        "rol": "usuario"
    },
    {
        "nombre": "Renata",
        "apellido": "Vargas",
        "email": "renata.vargas@email.com",
        "password": "Password123",
        "rol": "usuario"
    },
    {
        "nombre": "Andres",
        "apellido": "Flores",
        "email": "andres.flores@email.com",
        "password": "Password123",
        "rol": "admin"
    }
]


def insertar_usuarios():
    print("Insertando usuarios...\n")

    with httpx.Client(timeout=10.0) as client:
        for usuario in usuarios:
            try:
                response = client.post(URL, json=usuario)

                if response.status_code == 201:
                    print(
                        f"[OK] {usuario['email']} "
                        f"-> {response.status_code} Created"
                    )

                elif response.status_code == 409:
                    print(
                        f"[YA EXISTE] {usuario['email']} "
                        f"-> {response.status_code} Conflict"
                    )

                else:
                    print(
                        f"[ERROR] {usuario['email']} "
                        f"-> {response.status_code}"
                    )
                    print(response.text)

            except httpx.RequestError as error:
                print(
                    f"[ERROR DE CONEXIÓN] {usuario['email']}: {error}"
                )

    print("\nProceso terminado.")


if __name__ == "__main__":
    insertar_usuarios()