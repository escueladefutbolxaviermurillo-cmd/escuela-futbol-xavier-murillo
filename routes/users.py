from flask import Blueprint, render_template, request, redirect, url_for, flash
from database import db
from bson.objectid import ObjectId
from werkzeug.security import generate_password_hash
from utils.decorators import login_required, role_required
from datetime import datetime

users_bp = Blueprint('users', __name__, url_prefix='/users')

@users_bp.route('/')
@login_required
@role_required(['Administrador'])
def index():
    users = list(db.users.find().sort('full_name', 1)) if db is not None else []
    return render_template('users/index.html', users=users)

@users_bp.route('/create', methods=['GET', 'POST'])
@login_required
@role_required(['Administrador'])
def create():
    if request.method == 'POST':
        username = request.form.get('username', '').strip().lower()
        full_name = request.form.get('full_name', '').strip()
        role = request.form.get('role', 'Entrenador')
        password = request.form.get('password', '')

        if not username or not full_name or not password:
            flash("Todos los campos son obligatorios.", "danger")
            return render_template('users/create.html')

        # Verificar duplicado
        if db.users.find_one({"username": username}):
            flash("El nombre de usuario ya está registrado.", "warning")
            return render_template('users/create.html')

        new_user = {
            "username": username,
            "full_name": full_name,
            "role": role,
            "password_hash": generate_password_hash(password),
            "is_active": True,
            "created_at": datetime.utcnow()
        }

        db.users.insert_one(new_user)
        flash(f"Usuario '{username}' registrado exitosamente.", "success")
        return redirect(url_for('users.index'))

    return render_template('users/create.html')

@users_bp.route('/<user_id>/toggle-status', methods=['POST'])
@login_required
@role_required(['Administrador'])
def toggle_status(user_id):
    user = db.users.find_one({"_id": ObjectId(user_id)})
    if not user:
        flash("Usuario no encontrado.", "danger")
        return redirect(url_for('users.index'))

    new_status = not user.get('is_active', True)
    db.users.update_one({"_id": ObjectId(user_id)}, {"$set": {"is_active": new_status}})
    
    estado_texto = "activado" if new_status else "desactivado"
    flash(f"El usuario {user['username']} ha sido {estado_texto}.", "info")
    return redirect(url_for('users.index'))