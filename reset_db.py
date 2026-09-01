import os
from dotenv import load_dotenv
from pymongo import MongoClient
from werkzeug.security import generate_password_hash
from datetime import datetime

load_dotenv()

MONGO_URI = os.getenv('MONGO_URI', 'mongodb+srv://escueladefutbolxaviermurillo_db_user:8oid2ScS5v3fqVm3@escueladefutbol.6lsfvvl.mongodb.net/escuela_futbol_db?retryWrites=true&w=majority')

client = MongoClient(MONGO_URI)
db = client['escuela_futbol_db']

def limpiar_base_datos():
    print("Iniciando limpieza de la base de datos...")

    # 1. Vaciar colecciones operativas
    db.players.delete_many({})
    print("✔ Jugadores eliminados.")

    db.payments.delete_many({})
    print("✔ Pagos y recibos eliminados.")

    db.trainings.delete_many({})
    print("✔ Entrenamientos y asistencias eliminados.")

    db.categories.delete_many({})
    print("✔ Categorías eliminadas.")

    # 2. Limpiar usuarios y recrear el Administrador principal
    db.users.delete_many({})
    
    admin_user = {
        "username": "admin",
        "full_name": "Administrador Principal",
        "role": "Administrador",
        "password_hash": generate_password_hash("Admin1234*"), # Puedes cambiar la clave aquí
        "is_active": True,
        "created_at": datetime.utcnow()
    }
    db.users.insert_one(admin_user)
    print("✔ Usuarios eliminados y cuenta 'admin' recreada con contraseña 'Admin1234*'.")

    # 3. (Opcional) Crear categorías base por defecto
    categorias_defecto = [
        {"name": "Sub-6 (Iniciación)", "description": "Categoría formativa 4-6 años", "created_at": datetime.utcnow()},
        {"name": "Sub-8", "description": "Categoría formativa 7-8 años", "created_at": datetime.utcnow()},
        {"name": "Sub-10", "description": "Categoría formativa 9-10 años", "created_at": datetime.utcnow()},
        {"name": "Sub-12", "description": "Categoría intermedia 11-12 años", "created_at": datetime.utcnow()},
        {"name": "Sub-14", "description": "Categoría juvenil 13-14 años", "created_at": datetime.utcnow()}
    ]
    db.categories.insert_many(categorias_defecto)
    print("✔ Categorías base creadas.")

    print("\n Base de datos reseteada con éxito. Ya puedes ingresar con usuario 'admin' y clave 'Admin1234*'.")

if __name__ == "__main__":
    confirmacion = input("¿Estás seguro de que deseas borrar TODOS los datos de prueba? (s/n): ")
    if confirmacion.lower() == 's':
        limpiar_base_datos()
    else:
        print("Operación cancelada.")