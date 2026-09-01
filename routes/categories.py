from flask import Blueprint, render_template, request, redirect, url_for, flash
from database import db
from bson.objectid import ObjectId
from utils.decorators import login_required, role_required
from datetime import datetime

categories_bp = Blueprint('categories', __name__, url_prefix='/categories')

@categories_bp.route('/')
@login_required
@role_required(['Administrador'])
def index():
    categories = list(db.categories.find().sort('name', 1)) if db is not None else []
    
    # Calcular cantidad de jugadores activos asociados a cada categoría
    for cat in categories:
        cat['player_count'] = db.players.count_documents({
            "category_id": cat['_id'],
            "status": "Activo"
        }) if db is not None else 0

    return render_template('categories/index.html', categories=categories)

@categories_bp.route('/create', methods=['POST'])
@login_required
@role_required(['Administrador'])
def create():
    name = request.form.get('name', '').strip()
    description = request.form.get('description', '').strip()

    if not name:
        flash("El nombre de la categoría es obligatorio.", "danger")
        return redirect(url_for('categories.index'))

    # Evitar categorías duplicadas por nombre
    existing = db.categories.find_one({"name": {"$regex": f"^{name}$", "$options": "i"}})
    if existing:
        flash(f"La categoría '{name}' ya existe.", "warning")
        return redirect(url_for('categories.index'))

    new_cat = {
        "name": name,
        "description": description,
        "created_at": datetime.utcnow()
    }
    db.categories.insert_one(new_cat)
    flash(f"Categoría '{name}' creada con éxito.", "success")
    return redirect(url_for('categories.index'))

@categories_bp.route('/<category_id>/edit', methods=['POST'])
@login_required
@role_required(['Administrador'])
def edit(category_id):
    name = request.form.get('name', '').strip()
    description = request.form.get('description', '').strip()

    if not name:
        flash("El nombre de la categoría no puede estar vacío.", "danger")
        return redirect(url_for('categories.index'))

    db.categories.update_one(
        {"_id": ObjectId(category_id)},
        {"$set": {"name": name, "description": description}}
    )
    flash("Categoría actualizada correctamente.", "success")
    return redirect(url_for('categories.index'))

@categories_bp.route('/<category_id>/delete', methods=['POST'])
@login_required
@role_required(['Administrador'])
def delete(category_id):
    cat_oid = ObjectId(category_id)
    
    # Validar si tiene jugadores asociados antes de borrar
    assigned_players = db.players.count_documents({"category_id": cat_oid}) if db is not None else 0
    if assigned_players > 0:
        flash(f"No se puede eliminar la categoría porque tiene {assigned_players} jugador(es) asignado(s). Reasígnalos primero.", "danger")
        return redirect(url_for('categories.index'))

    db.categories.delete_one({"_id": cat_oid})
    flash("Categoría eliminada exitosamente.", "info")
    return redirect(url_for('categories.index'))