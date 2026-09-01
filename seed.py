from database import db
from werkzeug.security import generate_password_hash

def seed_database():
    if db is None:
        print("✗ No hay conexión a la base de datos.")
        return

    # 1. Crear usuario admin
    if not db.users.find_one({"username": "admin"}):
        admin_user = {
            "username": "admin",
            "password_hash": generate_password_hash("Admin1234*"),
            "full_name": "Administrador Principal",
            "role": "Administrador",
            "is_active": True
        }
        db.users.insert_one(admin_user)
        print("✓ Usuario 'admin' creado exitosamente.")
    else:
        print("ℹ Usuario 'admin' ya existe.")

    # 2. Crear categorías formativas
    default_categories = ["Sub-8", "Sub-10", "Sub-12", "Sub-14", "Sub-16", "Sub-18"]
    for cat in default_categories:
        db.categories.update_one({"name": cat}, {"$setOnInsert": {"name": cat}}, upsert=True)
    print("✓ Categorías formativas inicializadas.")

if __name__ == "__main__":
    seed_database()