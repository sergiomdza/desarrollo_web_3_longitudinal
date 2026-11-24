Equipo #5

· Descripción del módulo y de la entidad implementada.
El modulo nos permite crear, consultar y actualizar, eliminar usuarios mediante la Api desarollada con fastapi. Los datos son ingresados a una base de datos de MONGODB, en la base de datos nuestro equipo que trata de usuarios colocamos la coleccion con el nombre de auth_usuarios.


Las entidades o los modelos pydantic llevan 
- ID 
- NOMBRE 
- APELLIDO
- EMAIL
- ROLE 
- ACTIVOS 

Los roles son los siguientes : 
- ADMIND 
- USUARIO 
- MOD  

Al crear un usuario solicitamos mediante los requisitos de los modelos minimo 8 caracteres, aun que por el momento no se hace el cifrado o se almacena para realizar autentificacion.

Metodos         Rutas                       Descripcion 
GET          /usuarios/health               Comprueba el estado de la api y la conexion a MONGODB 
GET          /usuarios/                     Obtiene todos los usuarios
GET         /usuarios/{user_id}             Consultar usuario por id 
POST        /usuarios/create                Crea un usuario y verifica que no exista el email 
PUT         /usuarios/update/{user_id}      Actualiza los comapos del usuario 
DELETE      /usuarios/delete/{user_id}       Elimina un usuario por su id 

INTRUCIONES PARA LEVANTAR DESDE CERO 
Tener instalados Docker, Kind y kubectl, con Docker en ejecución. Ejecutar los siguientes comandos desde la raíz del repositorio

- Crear el clouster y namespace 
kind create cluster --name web3
kubectl create namespace proyecto-final

- Cargar la imagen de MongoDB y aplicar los manifiestos
docker pull mongo:7.0
kind load docker-image mongo:7.0 --name web3

kubectl apply -f kubernetes/mongo_statefulset.yaml
kubectl apply -f kubernetes/equipo_5/backend_deployment.yaml

- Verificar el despliegue

kubectl rollout status statefulset/mongo -n proyecto-final
kubectl rollout status deployment/backend -n proyecto-final
kubectl get pods -n proyecto-final
kubectl get services -n proyecto-final


- Habilitar el acceso local
kubectl port-forward service/backend-service 8000:8000 -n proyecto-final


- Probar el API
 poetry run fastapi dev app/main.py
