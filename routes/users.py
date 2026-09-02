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
    
    total_users = len(users)
    active_count = sum(1 for u in users if u.get('is_active', True))
    inactive_count = total_users - active_count

    # Distribución por Rol para el widget analítico
    role_counts = {
        'Administrador': sum(1 for u in users if u.get('role') == 'Administrador'),
        'Entrenador': sum(1 for u in users if u.get('role') == 'Entrenador'),
        'Representante': sum(1 for u in users if u.get('role') not in ['Administrador', 'Entrenador'])
    }

    # Porcentajes calculados para el gráfico de dona
    if total_users > 0:
        admin_pct = round((role_counts['Administrador'] / total_users) * 100)
        coach_pct = round((role_counts['Entrenador'] / total_users) * 100)
        rep_pct = max(0, 100 - admin_pct - coach_pct)
    else:
        admin_pct, coach_pct, rep_pct = 0, 0, 0

    role_stats = {
        'admin_pct': admin_pct,
        'coach_pct': coach_pct,
        'rep_pct': rep_pct,
        'counts': role_counts
    }

    return render_template(
        'users/index.html',
        users=users,
        total_users=total_users,
        active_count=active_count,
        inactive_count=inactive_count,
        role_stats=role_stats
    )

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