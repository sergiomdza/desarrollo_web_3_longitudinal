"""Configuración del servicio: todo se lee de variables de entorno
(inyectadas por el ConfigMap y el Secret de Kubernetes)."""
import os

MONGO_URI = os.environ["MONGO_URI"]
MONGO_DB = os.environ["MONGO_DB"]
MONGO_COLLECTION = os.environ["MONGO_COLLECTION"]