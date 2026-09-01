from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import check_password_hash
from database import db

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    # Si ya está autenticado, redirigir según su rol
    if 'user_id' in session:
        if session.get('role') == 'Representante':
            return redirect(url_for('portal.index'))
        return redirect(url_for('dashboard.index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        if not username or not password:
            flash("Por favor completa todos los campos.", "warning")
            return render_template('login.html')

        user = db.users.find_one({"username": username, "is_active": True}) if db is not None else None

        if user and check_password_hash(user.get('password_hash', ''), password):
            session.clear()
            session['user_id'] = str(user['_id'])
            session['username'] = user['username']
            session['role'] = user.get('role', 'Representante')
            session['full_name'] = user.get('full_name', user['username'])
            
            flash(f"¡Bienvenido, {session['full_name']}!", "success")
            
            # Redirección diferenciada por rol
            if session['role'] == 'Representante':
                return redirect(url_for('portal.index'))
            return redirect(url_for('dashboard.index'))
        else:
            flash("Usuario o contraseña incorrectos.", "danger")

    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    flash("Has cerrado sesión correctamente.", "info")
    return redirect(url_for('auth.login'))