import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")

try:
    client = MongoClient(MONGO_URI)
    # Especificar el nombre directo de la base de datos
    db = client["escuela_futbol_db"]
    # Ping para verificar conexión real
    client.admin.command('ping')
    print("✓ Conexión exitosa a MongoDB Atlas")
except Exception as e:
    print(f"✗ Error al conectar a MongoDB: {e}")
    db = None